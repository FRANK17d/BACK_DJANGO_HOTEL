from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from datetime import datetime, timedelta, date
from decimal import Decimal
from reservations.models import Reservation, Room, ReservationRoom
from cajacobros.models import Payment
from mantenimiento.models import BlockedRoom


@api_view(['GET'])
def dashboard_metrics(request):
    """Métricas principales del dashboard"""
    if not hasattr(request, 'firebase_user') or not request.firebase_user:
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    
    now = timezone.localtime()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = current_month_start - timedelta(days=1)
    
    # Ingresos del mes actual
    current_month_payments = Payment.objects.filter(
        created_at__gte=current_month_start,
        status='Completado'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Ingresos del mes anterior
    last_month_payments = Payment.objects.filter(
        created_at__gte=last_month_start,
        created_at__lte=last_month_end,
        status='Completado'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Calcular porcentaje de cambio
    monthly_change = 0
    if last_month_payments > 0:
        monthly_change = ((current_month_payments - last_month_payments) / last_month_payments) * 100
    
    # Ingresos totales (todos los tiempos)
    total_payments = Payment.objects.filter(
        status='Completado'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Ingresos totales del mes anterior (para comparación)
    total_payments_last_month = Payment.objects.filter(
        created_at__lte=last_month_end,
        status='Completado'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    total_change = 0
    if total_payments_last_month > 0:
        total_change = ((total_payments - total_payments_last_month) / total_payments_last_month) * 100
    
    # Tasa de ocupación
    total_rooms = Room.objects.count()
    today = now.date()
    
    # Reservas activas hoy (check-in <= hoy <= check-out)
    active_reservations = Reservation.objects.filter(
        check_in__lte=today,
        check_out__gte=today,
        status__in=['Confirmada', 'Check-in']
    ).count()
    
    occupancy_rate = 0
    if total_rooms > 0:
        occupancy_rate = (active_reservations / total_rooms) * 100
    
    # Tasa de ocupación del mes anterior (mismo día)
    last_month_date = today - timedelta(days=30)
    active_reservations_last_month = Reservation.objects.filter(
        check_in__lte=last_month_date,
        check_out__gte=last_month_date,
        status__in=['Confirmada', 'Check-in']
    ).count()
    
    occupancy_rate_last_month = 0
    if total_rooms > 0:
        occupancy_rate_last_month = (active_reservations_last_month / total_rooms) * 100
    
    occupancy_change = occupancy_rate - occupancy_rate_last_month
    
    # ADR Promedio (Average Daily Rate)
    # Calcular ADR del mes actual
    current_month_reservations = Reservation.objects.filter(
        check_in__gte=current_month_start.date(),
        check_in__lt=(current_month_start + timedelta(days=32)).replace(day=1).date()
    )
    
    adr = 0
    if current_month_reservations.exists():
        total_revenue = current_month_reservations.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')
        total_nights = sum([
            (r.check_out - r.check_in).days for r in current_month_reservations
        ])
        if total_nights > 0:
            adr = float(total_revenue) / total_nights
    
    # ADR del mes anterior
    last_month_reservations = Reservation.objects.filter(
        check_in__gte=last_month_start.date(),
        check_in__lte=last_month_end.date()
    )
    
    adr_last_month = 0
    if last_month_reservations.exists():
        total_revenue_last = last_month_reservations.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')
        total_nights_last = sum([
            (r.check_out - r.check_in).days for r in last_month_reservations
        ])
        if total_nights_last > 0:
            adr_last_month = float(total_revenue_last) / total_nights_last
    
    adr_change = adr - adr_last_month
    adr_change_percent = 0
    if adr_last_month > 0:
        adr_change_percent = (adr_change / adr_last_month) * 100
    
    return Response({
        'monthly_revenue': {
            'amount': float(current_month_payments),
            'change_percent': round(monthly_change, 1)
        },
        'total_revenue': {
            'amount': float(total_payments),
            'change_percent': round(total_change, 1)
        },
        'occupancy_rate': {
            'rate': round(occupancy_rate, 1),
            'change_percent': round(occupancy_change, 1)
        },
        'adr': {
            'amount': round(adr, 2),
            'change_percent': round(adr_change_percent, 1)
        }
    })


@api_view(['GET'])
def monthly_revenue_chart(request):
    """Ingresos mensuales de los últimos 12 meses"""
    if not hasattr(request, 'firebase_user') or not request.firebase_user:
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    
    now = timezone.localtime()
    data = []
    
    for i in range(11, -1, -1):  # Últimos 12 meses
        month_start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        
        month_payments = Payment.objects.filter(
            created_at__gte=month_start,
            created_at__lt=month_end,
            status='Completado'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        data.append(float(month_payments))
    
    return Response({'data': data})


@api_view(['GET'])
def payment_methods_chart(request):
    """Distribución de ingresos por método de pago"""
    if not hasattr(request, 'firebase_user') or not request.firebase_user:
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    
    now = timezone.localtime()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    methods = ['Yape', 'Efectivo', 'Tarjeta', 'Transferencia']
    data = {}
    
    for method in methods:
        total = Payment.objects.filter(
            created_at__gte=current_month_start,
            method=method,
            status='Completado'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        data[method] = float(total)
    
    return Response({'data': data})


@api_view(['GET'])
def occupancy_weekly_chart(request):
    """Tasa de ocupación semanal (últimas 7 semanas)"""
    if not hasattr(request, 'firebase_user') or not request.firebase_user:
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    
    total_rooms = Room.objects.count()
    if total_rooms == 0:
        return Response({'data': [0] * 7})
    
    now = timezone.localtime()
    today = now.date()
    data = []
    
    for i in range(6, -1, -1):  # Últimas 7 semanas
        week_date = today - timedelta(days=7 * i)
        active_reservations = Reservation.objects.filter(
            check_in__lte=week_date,
            check_out__gte=week_date,
            status__in=['Confirmada', 'Check-in']
        ).count()
        
        occupancy = (active_reservations / total_rooms) * 100 if total_rooms > 0 else 0
        data.append(round(occupancy, 1))
    
    return Response({'data': data})


def get_auto_status(reservation):
    """Calcula el estado automático basado en fechas y horas (igual que el frontend)"""
    s = reservation.status
    if s and s.lower() == 'cancelada':
        return 'Cancelada'
    
    ci = reservation.check_in
    co = reservation.check_out
    if not ci or not co:
        return s or 'Confirmada'
    
    now = timezone.localtime()
    today = now.date()
    now_hm = now.strftime('%H:%M')
    
    arr_time = reservation.arrival_time
    arr_hm = arr_time.strftime('%H:%M') if arr_time else ''
    dep_time = reservation.departure_time
    dep_hm = dep_time.strftime('%H:%M') if dep_time else ''
    
    # Antes del check-in
    if today < ci:
        return 'Confirmada'
    
    # Si hay hora de salida configurada
    if dep_hm:
        if today < co:
            if today >= ci:
                if today == ci and arr_hm and now_hm < arr_hm:
                    return 'Confirmada'
                return 'Check-in'
            return 'Confirmada'
        
        if today >= co:
            if today == co:
                if now_hm >= dep_hm:
                    return 'Check-out'
                else:
                    return 'Check-in'
            return 'Check-out'
    
    # Si NO hay hora de salida configurada
    if ci == co:
        if today < ci:
            return 'Confirmada'
        if today == ci:
            if arr_hm and now_hm < arr_hm:
                return 'Confirmada'
            return 'Check-in'
        if today > ci:
            return 'Check-out'
    else:
        if today == ci:
            if arr_hm and now_hm < arr_hm:
                return 'Confirmada'
            return 'Check-in'
        if today > ci and today < co:
            return 'Check-in'
        if today >= co:
            return 'Check-out'
    
    return 'Check-in'


def sync_reservation_status(reservation):
    """Sincroniza el estado calculado con la base de datos si es diferente"""
    if reservation.status and reservation.status.lower() == 'cancelada':
        return reservation.status  # No cambiar reservas canceladas
    
    auto_status = get_auto_status(reservation)
    if reservation.status != auto_status:
        reservation.status = auto_status
        reservation.save(update_fields=['status'])
    return auto_status


def sync_room_statuses():
    """Sincroniza el estado de todas las habitaciones basándose en reservas y bloqueos"""
    today = timezone.localtime().date()
    updated_count = 0
    
    # Obtener habitaciones bloqueadas actualmente
    blocked_rooms = set()
    for br in BlockedRoom.objects.filter(blocked_until__gte=today):
        blocked_rooms.add(str(br.room).strip())
    
    # Obtener habitaciones ocupadas (reservas con estado Check-in)
    occupied_rooms = set()
    checkin_reservations = Reservation.objects.filter(status='Check-in')
    for res in checkin_reservations:
        # Habitación principal
        if res.room_label:
            occupied_rooms.add(str(res.room_label).strip())
        # Habitaciones asignadas
        for ar in res.assigned_rooms.all():
            occupied_rooms.add(str(ar.room_code).strip())
    
    # Actualizar estado de cada habitación
    for room in Room.objects.all():
        room_code = str(room.code).strip()
        
        if room_code in blocked_rooms:
            new_status = 'Bloqueada'
        elif room_code in occupied_rooms:
            new_status = 'Ocupada'
        else:
            new_status = 'Disponible'
        
        if room.status != new_status:
            room.status = new_status
            room.save(update_fields=['status'])
            updated_count += 1
    
    return updated_count


@api_view(['GET'])
def today_checkins_checkouts(request):
    """Check-ins y check-outs del día"""
    if not hasattr(request, 'firebase_user') or not request.firebase_user:
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    
    today = timezone.localtime().date()
    
    # Sincronizar estados de todas las reservas activas (no canceladas)
    active_reservations = Reservation.objects.exclude(status='Cancelada')
    for res in active_reservations:
        sync_reservation_status(res)
    
    # Sincronizar estados de habitaciones
    sync_room_statuses()
    
    # Check-ins de hoy - Reservas con estado "Confirmada" (pendientes de llegar)
    checkins = Reservation.objects.filter(
        check_in=today,
        status='Confirmada'
    ).order_by('arrival_time', 'created_at')[:5]
    
    checkins_data = []
    for res in checkins:
        checkins_data.append({
            'id': res.id,
            'reservation_id': res.reservation_id,
            'name': res.guest_name,
            'room': res.room_label,
            'time': res.arrival_time.strftime('%H:%M') if res.arrival_time else '--:--'
        })
    
    # Check-outs de hoy - Reservas con estado "Check-in" (aún hospedadas, pendientes de salir)
    checkouts = Reservation.objects.filter(
        check_out=today,
        status='Check-in'
    ).order_by('created_at')[:5]
    
    checkouts_data = []
    for res in checkouts:
        checkouts_data.append({
            'id': res.id,
            'reservation_id': res.reservation_id,
            'name': res.guest_name,
            'room': res.room_label,
            'time': res.departure_time.strftime('%H:%M') if res.departure_time else '11:00'
        })
    
    return Response({
        'checkins': checkins_data,
        'checkouts': checkouts_data
    })


@api_view(['POST'])
def sync_all_statuses(request):
    """Sincroniza el estado de todas las reservas y habitaciones"""
    if not hasattr(request, 'firebase_user') or not request.firebase_user:
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Sincronizar reservas
    reservations_updated = 0
    active_reservations = Reservation.objects.exclude(status='Cancelada')
    
    for res in active_reservations:
        old_status = res.status
        new_status = sync_reservation_status(res)
        if old_status != new_status:
            reservations_updated += 1
    
    # Sincronizar habitaciones
    rooms_updated = sync_room_statuses()
    
    return Response({
        'message': 'Estados sincronizados correctamente',
        'reservations_updated': reservations_updated,
        'rooms_updated': rooms_updated,
        'total_reservations': active_reservations.count(),
        'total_rooms': Room.objects.count()
    })


@api_view(['GET'])
def recent_reservations(request):
    """Reservas recientes (últimas 4)"""
    if not hasattr(request, 'firebase_user') or not request.firebase_user:
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    
    reservations = Reservation.objects.all().order_by('-created_at')[:4]
    
    data = []
    for res in reservations:
        guests_str = f"{res.num_adults} Adulto{'s' if res.num_adults > 1 else ''}"
        if res.num_children > 0:
            guests_str += f", {res.num_children} Niño{'s' if res.num_children > 1 else ''}"
        
        data.append({
            'id': res.id,
            'guestName': res.guest_name,
            'room': res.room_label,
            'checkIn': res.check_in.strftime('%Y-%m-%d'),
            'checkOut': res.check_out.strftime('%Y-%m-%d'),
            'guests': guests_str,
            'total': f"S/ {res.total_amount:.2f}",
            'status': res.status
        })
    
    return Response({'reservations': data})


@api_view(['GET'])
def statistics_chart(request):
    """Ingresos anuales (últimos 12 meses)"""
    if not hasattr(request, 'firebase_user') or not request.firebase_user:
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    
    now = timezone.localtime()
    income_data = []
    labels = []
    
    month_names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    
    for i in range(11, -1, -1):  # Últimos 12 meses (año completo)
        month_start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        
        # Ingresos (pagos completados)
        income = Payment.objects.filter(
            created_at__gte=month_start,
            created_at__lt=month_end,
            status='Completado'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        income_data.append(float(income))
        labels.append(month_names[month_start.month - 1])
    
    return Response({
        'income': income_data,
        'labels': labels
    })
