from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Reservation, Room, ReservationRoom, DayNote
from .serializers import ReservationSerializer
from django.utils.dateparse import parse_date, parse_time
from .models import Companion
import os
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from django.conf import settings


@api_view(['GET'])
def list_reservations(request):
    if not hasattr(request, 'firebase_user'):
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    qs = Reservation.objects.all()
    data = ReservationSerializer(qs, many=True).data
    return Response({'reservations': data})


@api_view(['POST'])
def create_reservation(request):
    if not hasattr(request, 'firebase_user'):
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    payload = request.data or {}
    channel = payload.get('channel')
    guest = payload.get('guest')
    room = payload.get('room')
    check_in = parse_date(payload.get('checkIn'))
    check_out = parse_date(payload.get('checkOut'))
    total = payload.get('total')
    status_text = payload.get('status') or 'Confirmada'
    paid = bool(payload.get('paid'))
    document_type = payload.get('documentType')
    document_number = payload.get('documentNumber')
    arrival_time = parse_time(payload.get('arrivalTime')) if payload.get('arrivalTime') else None
    num_people = int(payload.get('numPeople') or 1)
    num_adults = int(payload.get('numAdults') or num_people)
    num_children = int(payload.get('numChildren') or 0)
    num_rooms = int(payload.get('numRooms') or 1)
    address = payload.get('address')
    department = payload.get('department')
    province = payload.get('province')
    district = payload.get('district')
    taxpayer_type = payload.get('taxpayerType')
    business_status = payload.get('businessStatus')
    business_condition = payload.get('businessCondition')
    room_type = payload.get('roomType')

    try:
        total_amount = float(str(total).replace('S/', '').strip()) if total is not None else 0
    except Exception:
        total_amount = 0

    reservation = Reservation.objects.create(
        channel=channel or 'Venta Directa',
        guest_name=guest or '',
        room_label=room or '',
        check_in=check_in,
        check_out=check_out,
        total_amount=total_amount,
        status=status_text,
        paid=paid,
        document_type=document_type,
        document_number=document_number,
        arrival_time=arrival_time,
        num_people=num_people,
        num_adults=num_adults,
        num_children=num_children,
        num_rooms=num_rooms,
        address=address,
        department=department,
        province=province,
        district=district,
        taxpayer_type=taxpayer_type,
        business_status=business_status,
        business_condition=business_condition,
        room_type=room_type,
    )
    rooms_payload = payload.get('rooms') or []
    if isinstance(rooms_payload, list) and rooms_payload:
        if not reservation.room_label:
            reservation.room_label = str(rooms_payload[0])
            reservation.save(update_fields=['room_label'])
        for code in rooms_payload:
            if code:
                ReservationRoom.objects.create(reservation=reservation, room_code=str(code))
    companions_payload = payload.get('companions') or []
    for item in companions_payload:
        name = item.get('name') or ''
        dt = item.get('documentType')
        dn = item.get('documentNumber')
        address = item.get('address')
        department = item.get('department')
        province = item.get('province')
        district = item.get('district')
        taxpayer_type = item.get('taxpayerType')
        business_status = item.get('businessStatus')
        business_condition = item.get('businessCondition')
        if name or dn:
            Companion.objects.create(
                reservation=reservation,
                name=name,
                document_type=dt,
                document_number=dn,
                address=address,
                department=department,
                province=province,
                district=district,
                taxpayer_type=taxpayer_type,
                business_status=business_status,
                business_condition=business_condition,
            )
    data = ReservationSerializer(reservation).data
    return Response({'reservation': data}, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
def reservation_detail(request, reservation_id):
    if not hasattr(request, 'firebase_user'):
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        obj = Reservation.objects.get(reservation_id=reservation_id)
    except Reservation.DoesNotExist:
        return Response({'error': 'Reserva no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        data = ReservationSerializer(obj).data
        return Response({'reservation': data})

    if request.method == 'PATCH':
        payload = request.data or {}
        for key in ['channel', 'status']:
            val = payload.get(key)
            if val is not None:
                setattr(obj, key if key != 'status' else 'status', val)
        if payload.get('guest') is not None:
            obj.guest_name = payload.get('guest')
        if payload.get('room') is not None:
            obj.room_label = payload.get('room')
        if payload.get('checkIn') is not None:
            obj.check_in = parse_date(payload.get('checkIn'))
        if payload.get('checkOut') is not None:
            obj.check_out = parse_date(payload.get('checkOut'))
        if payload.get('arrivalTime') is not None:
            obj.arrival_time = parse_time(payload.get('arrivalTime'))
        if payload.get('paid') is not None:
            obj.paid = bool(payload.get('paid'))
        if payload.get('roomType') is not None:
            obj.room_type = payload.get('roomType')
        if payload.get('total') is not None:
            try:
                obj.total_amount = float(str(payload.get('total')).replace('S/', '').strip())
            except Exception:
                pass
        obj.save()
        data = ReservationSerializer(obj).data
        return Response({'reservation': data})

    if request.method == 'DELETE':
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def calendar_events(request):
    if not hasattr(request, 'firebase_user'):
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    events = []
    for r in Reservation.objects.all():
        if not r.check_in or not r.check_out:
            continue
        ch = r.channel or ''
        if 'Booking' in ch:
            cal = 'Booking'
        elif 'WhatsApp' in ch:
            cal = 'WhatsApp'
        elif 'Venta' in ch:
            cal = 'DirectSale'
        else:
            cal = 'DirectSale'
        events.append({
            'id': r.reservation_id,
            'title': f"{r.guest_name} - {r.room_label}",
            'start': str(r.check_in),
            'end': str(r.check_out),
            'extendedProps': {'calendar': cal},
        })
    return Response({'events': events})


@api_view(['GET'])
def calendar_notes(request):
    if not hasattr(request, 'firebase_user'):
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    items = []
    for n in DayNote.objects.all():
        items.append({'date': str(n.date), 'text': n.text or ''})
    return Response({'notes': items})


@api_view(['PUT', 'DELETE'])
def calendar_note_detail(request, date):
    if not hasattr(request, 'firebase_user'):
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    d = parse_date(date)
    if not d:
        return Response({'error': 'Fecha inválida'}, status=status.HTTP_400_BAD_REQUEST)
    if request.method == 'DELETE':
        DayNote.objects.filter(date=d).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    payload = request.data or {}
    text = payload.get('text') or ''
    obj, _ = DayNote.objects.update_or_create(date=d, defaults={'text': text})
    return Response({'note': {'date': str(obj.date), 'text': obj.text or ''}})


@api_view(['GET'])
def available_rooms(request):
    ci = request.GET.get('check_in')
    co = request.GET.get('check_out')
    if not ci or not co:
        return Response({'error': 'Parámetros incompletos'}, status=status.HTTP_400_BAD_REQUEST)
    check_in = parse_date(ci)
    check_out = parse_date(co)
    if not check_in or not check_out:
        return Response({'error': 'Fechas inválidas'}, status=status.HTTP_400_BAD_REQUEST)
    occupied = set()
    for r in Reservation.objects.all():
        if not r.check_in or not r.check_out:
            continue
        if r.check_in < check_out and r.check_out > check_in:
            if r.room_label:
                occupied.add(r.room_label)
            for ar in r.assigned_rooms.all():
                occupied.add(ar.room_code)
    items = []
    for rm in Room.objects.all():
        if rm.code not in occupied:
            items.append({'code': rm.code, 'floor': rm.floor, 'type': rm.type})
    return Response({'rooms': items})

@api_view(['GET'])
def lookup_document(request):
    if not hasattr(request, 'firebase_user'):
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    doc_type = (request.GET.get('type') or '').upper()
    number = request.GET.get('number') or ''
    if not doc_type or not number:
        return Response({'error': 'Parámetros incompletos'}, status=status.HTTP_400_BAD_REQUEST)
    token = getattr(settings, 'LOOKUP_API_TOKEN', None)
    urls = {
        'DNI': os.environ.get('LOOKUP_DNI_URL'),
        'RUC': os.environ.get('LOOKUP_RUC_URL'),
        'CE': os.environ.get('LOOKUP_CE_URL'),
    }
    url = urls.get(doc_type)
    if not url:
        if doc_type == 'DNI':
            url = f"https://api.factiliza.com/v1/dni/info/{number}"
        elif doc_type == 'RUC':
            url = f"https://api.factiliza.com/v1/ruc/info/{number}"
        elif doc_type == 'CE':
            url = f"https://api.factiliza.com/v1/cee/info/{number}"
        else:
            return Response({'error': 'Proveedor no configurado'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        url = url.replace('{number}', number).replace('{dni}', number).replace('{ruc}', number).replace('{cee}', number)
    headers = {}
    if token:
        headers['Authorization'] = f"Bearer {token}"
    try:
        req = Request(url, headers=headers)
        with urlopen(req) as resp:
            raw = resp.read().decode('utf-8')
            payload = json.loads(raw)
    except HTTPError as e:
        return Response({'error': f'HTTP {e.code}'}, status=status.HTTP_502_BAD_GATEWAY)
    except URLError:
        return Response({'error': 'No se pudo conectar al proveedor'}, status=status.HTTP_502_BAD_GATEWAY)
    success = bool(payload.get('success'))
    data = payload.get('data') or {}
    if not success:
        return Response({'error': payload.get('message') or 'Consulta fallida'}, status=status.HTTP_400_BAD_REQUEST)
    if doc_type == 'DNI':
        name = data.get('nombre_completo') or (
            ((data.get('nombres') or '') + ' ' + (data.get('apellido_paterno') or '') + ' ' + (data.get('apellido_materno') or '')).strip()
        )
    elif doc_type == 'RUC':
        name = data.get('nombre_o_razon_social')
    else:
        name = (
            ((data.get('nombres') or '') + ' ' + (data.get('apellido_paterno') or '') + ' ' + (data.get('apellido_materno') or '')).strip()
        )
    return Response({'name': name, 'raw': payload})
