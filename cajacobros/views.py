from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Sum
from django.db import DatabaseError, OperationalError
from decimal import Decimal, InvalidOperation
from datetime import datetime
import pytz
from .models import Payment, Receipt


def _format_time(dt):
    if not dt:
        return ''
    return timezone.localtime(dt).strftime('%I:%M %p')


def _get_date_range_for_totals(request):
    """Obtiene el rango de fechas desde el parámetro 'date' o usa la fecha de hoy.
    Retorna los datetimes en UTC para comparar con los almacenados en la BD."""
    date_str = request.GET.get('date')
    if date_str:
        try:
            # Parsear la fecha en formato YYYY-MM-DD
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            # Crear datetime en timezone local (Lima)
            local_tz = timezone.get_current_timezone()
            # Compatible con pytz y zoneinfo
            start_naive = datetime.combine(target_date, datetime.min.time())
            end_naive = datetime.combine(target_date, datetime.max.time())
            # Si es pytz, usar localize; si es zoneinfo, usar replace
            if hasattr(local_tz, 'localize'):
                start_local = local_tz.localize(start_naive)
                end_local = local_tz.localize(end_naive)
            else:
                start_local = start_naive.replace(tzinfo=local_tz)
                end_local = end_naive.replace(tzinfo=local_tz)
            # Convertir a UTC para comparar con los datetimes en la BD
            start = start_local.astimezone(pytz.UTC)
            end = end_local.astimezone(pytz.UTC)
            return start, end
        except (ValueError, TypeError):
            # Si hay error al parsear, usar fecha de hoy
            pass
    
    # Por defecto, usar fecha de hoy
    now = timezone.localtime()
    start_local = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    # Convertir a UTC
    start = start_local.astimezone(pytz.UTC)
    end = end_local.astimezone(pytz.UTC)
    return start, end


@api_view(['GET'])
def list_today_transactions(request):
    if not hasattr(request, 'firebase_user'):
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    start, end = _get_date_range_for_totals(request)
    qs = Payment.objects.filter(created_at__gte=start, created_at__lte=end)
    data = []
    for p in qs:
        data.append({
            'id': p.id,
            'transactionId': p.transaction_id,
            'type': p.type,
            'guest': p.guest_name,
            'method': p.method,
            'amount': float(p.amount),
            'time': _format_time(p.created_at),
            'status': p.status,
        })
    return Response({'transactions': data})


@api_view(['POST'])
def create_payment(request):
    if not getattr(request, 'firebase_user', None):
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    payload = request.data or {}
    t = payload.get('type') or 'Pago de Reserva'
    g = payload.get('guest') or ''
    m = payload.get('method') or 'Efectivo'
    a = payload.get('amount')
    rcode = payload.get('reservationCode')
    if a is None:
        return Response({'error': 'Falta monto'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        amount_val = Decimal(str(a))
    except (InvalidOperation, TypeError, ValueError):
        return Response({'error': 'Monto inválido'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        existing = list(Payment.objects.filter(transaction_id__startswith='TXN-').values_list('transaction_id', flat=True))
        max_n = 0
        for tid in existing:
            parts = str(tid).split('-')
            if len(parts) == 2 and parts[0] == 'TXN':
                try:
                    n = int(parts[1])
                    if n > max_n:
                        max_n = n
                except Exception:
                    pass
        next_n = max_n + 1
        txn = f"TXN-{str(next_n).zfill(3)}"
        while Payment.objects.filter(transaction_id=txn).exists():
            next_n += 1
            txn = f"TXN-{str(next_n).zfill(3)}"
        p = Payment.objects.create(
            transaction_id=txn,
            type=t,
            guest_name=g,
            method=m,
            amount=amount_val,
            status='Completado',
            reservation_code=rcode,
        )
    except (DatabaseError, OperationalError) as e:
        return Response({'error': 'Error de base de datos', 'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response({
        'id': p.id,
        'transactionId': p.transaction_id,
        'type': p.type,
        'guest': p.guest_name,
        'method': p.method,
        'amount': float(p.amount),
        'time': _format_time(p.created_at),
        'status': p.status,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def today_totals(request):
    if not hasattr(request, 'firebase_user'):
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    start, end = _get_date_range_for_totals(request)
    qs = Payment.objects.filter(created_at__gte=start, created_at__lte=end)
    by_method = {}
    for method in ['Yape', 'Efectivo', 'Tarjeta', 'Transferencia']:
        by_method[method] = float(qs.filter(method=method).aggregate(total=Sum('amount'))['total'] or 0)
    total = float(qs.aggregate(total=Sum('amount'))['total'] or 0)
    return Response({'totals': {'methods': by_method, 'total': total}})


@api_view(['GET'])
def today_clients(request):
    if not hasattr(request, 'firebase_user'):
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    now = timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    qs = Payment.objects.filter(created_at__gte=start, created_at__lte=end)
    agg = {}
    for p in qs:
        key = p.guest_name or '—'
        agg[key] = float(agg.get(key, 0)) + float(p.amount)
    clients = [{'guest': k, 'total': v} for k, v in agg.items()]
    total = float(qs.aggregate(total=Sum('amount'))['total'] or 0)
    return Response({'clients': clients, 'total': total})


@api_view(['GET'])
def all_clients(request):
    if not hasattr(request, 'firebase_user'):
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    qs = Payment.objects.filter(status='Completado')
    agg = {}
    for p in qs:
        key = p.guest_name or '—'
        agg[key] = float(agg.get(key, 0)) + float(p.amount)
    clients = [{'guest': k, 'total': v} for k, v in agg.items()]
    total = float(qs.aggregate(total=Sum('amount'))['total'] or 0)
    return Response({'clients': clients, 'total': total})


@api_view(['POST'])
def emit_receipt(request):
    if not hasattr(request, 'firebase_user'):
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    payload = request.data or {}
    pid = payload.get('paymentId')
    if not pid:
        return Response({'error': 'Falta paymentId'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        p = Payment.objects.get(id=pid)
    except Payment.DoesNotExist:
        return Response({'error': 'Pago no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    r = Receipt.objects.create(
        payment=p,
        numero=payload.get('numero') or '',
        fecha=payload.get('fecha'),
        senores=payload.get('senores') or '',
        direccion=payload.get('direccion') or '',
        dni=payload.get('dni') or '',
        concepto=payload.get('concepto') or '',
        importe=payload.get('importe') or p.amount,
        total=payload.get('total') or p.amount,
        son=payload.get('son') or '',
        cancelado_fecha=payload.get('canceladoFecha') or timezone.localdate(),
    )
    return Response({'receipt': {
        'id': r.id,
        'paymentId': p.id,
        'numero': r.numero,
        'fecha': str(r.fecha),
        'senores': r.senores,
        'direccion': r.direccion,
        'dni': r.dni,
        'concepto': r.concepto,
        'importe': float(r.importe),
        'total': float(r.total),
        'son': r.son,
        'canceladoFecha': str(r.cancelado_fecha),
    }}, status=status.HTTP_201_CREATED)
