from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime, date, time, timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import WaterHeatingSystem, BriquetteChange, MaintenanceIssue, BlockedRoom


@api_view(["GET"])
def system_status(request):
    """Obtiene el estado del sistema de agua caliente"""
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    system = WaterHeatingSystem.get_instance()
    
    # Formatear fecha y hora para el frontend
    last_maintenance = None
    if system.last_maintenance_date:
        last_maintenance = {
            "date": system.last_maintenance_date.strftime("%Y-%m-%d"),
            "time": system.last_maintenance_time.strftime("%I:%M %p") if system.last_maintenance_time else None,
        }
    
    next_maintenance = None
    if system.next_maintenance_date:
        next_maintenance = {
            "date": system.next_maintenance_date.strftime("%Y-%m-%d"),
            "time": system.next_maintenance_time.strftime("%I:%M %p") if system.next_maintenance_time else None,
        }
    
    return Response({
        "operationalStatus": system.operational_status,
        "briquettesThisMonth": system.briquettes_this_month,
        "lastMaintenance": last_maintenance,
        "nextMaintenance": next_maintenance,
    })


@api_view(["POST"])
def update_system_status(request):
    """Actualiza el estado del sistema"""
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    system = WaterHeatingSystem.get_instance()
    
    payload = request.data or {}
    
    if "operationalStatus" in payload:
        system.operational_status = payload["operationalStatus"]
    
    if "briquettesThisMonth" in payload:
        system.briquettes_this_month = max(0, int(payload.get("briquettesThisMonth", 0)))
    
    if "lastMaintenance" in payload:
        lm = payload["lastMaintenance"]
        if lm.get("date"):
            system.last_maintenance_date = datetime.strptime(lm["date"], "%Y-%m-%d").date()
        if lm.get("time"):
            # Convertir hora de formato "HH:MM" a time object
            time_str = lm["time"]
            if ":" in time_str:
                parts = time_str.split(":")
                system.last_maintenance_time = time(int(parts[0]), int(parts[1]))
    
    if "nextMaintenance" in payload:
        nm = payload["nextMaintenance"]
        if nm.get("date"):
            system.next_maintenance_date = datetime.strptime(nm["date"], "%Y-%m-%d").date()
        if nm.get("time"):
            time_str = nm["time"]
            if ":" in time_str:
                parts = time_str.split(":")
                system.next_maintenance_time = time(int(parts[0]), int(parts[1]))
    
    system.save()
    
    return Response({
        "operationalStatus": system.operational_status,
        "briquettesThisMonth": system.briquettes_this_month,
        "lastMaintenance": {
            "date": system.last_maintenance_date.strftime("%Y-%m-%d") if system.last_maintenance_date else None,
            "time": system.last_maintenance_time.strftime("%I:%M %p") if system.last_maintenance_time else None,
        },
        "nextMaintenance": {
            "date": system.next_maintenance_date.strftime("%Y-%m-%d") if system.next_maintenance_date else None,
            "time": system.next_maintenance_time.strftime("%I:%M %p") if system.next_maintenance_time else None,
        },
    })


@api_view(["GET"])
def briquette_history(request):
    """Obtiene el historial de cambios de briquetas"""
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    history = []
    for change in BriquetteChange.objects.all()[:50]:  # Limitar a 50 registros
        history.append({
            "id": change.id,
            "date": change.date.strftime("%Y-%m-%d"),
            "time": change.time.strftime("%I:%M %p"),
            "quantity": change.quantity,
        })
    
    return Response({"history": history})


@api_view(["POST"])
def register_briquette_change(request):
    """Registra un cambio de briquetas"""
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    payload = request.data or {}
    
    quantity = int(payload.get("quantity", 0))
    change_date = payload.get("date")
    change_time = payload.get("time")
    operational_status = payload.get("operationalStatus")
    
    if not change_date or not change_time:
        return Response({"error": "Fecha y hora son requeridas"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Crear el registro de cambio
    try:
        date_obj = datetime.strptime(change_date, "%Y-%m-%d").date()
        time_parts = change_time.split(":")
        time_obj = time(int(time_parts[0]), int(time_parts[1]))
        
        change = BriquetteChange.objects.create(
            date=date_obj,
            time=time_obj,
            quantity=quantity
        )
        
        # Actualizar el sistema
        system = WaterHeatingSystem.get_instance()
        system.briquettes_this_month += quantity
        if operational_status:
            system.operational_status = operational_status
        
        # Actualizar último mantenimiento
        system.last_maintenance_date = date_obj
        system.last_maintenance_time = time_obj
        
        # Calcular próximo cambio: 7 horas después del último cambio
        last_datetime = datetime.combine(date_obj, time_obj)
        next_datetime = last_datetime + timedelta(hours=7)
        system.next_maintenance_date = next_datetime.date()
        system.next_maintenance_time = next_datetime.time()
        
        system.save()
        
        return Response({
            "id": change.id,
            "date": change.date.strftime("%Y-%m-%d"),
            "time": change.time.strftime("%I:%M %p"),
            "quantity": change.quantity,
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def maintenance_issues(request):
    """Obtiene las incidencias de mantenimiento"""
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    issues = []
    for issue in MaintenanceIssue.objects.all()[:100]:  # Limitar a 100 registros
        issues.append({
            "id": issue.id,
            "room": issue.room,
            "problem": issue.problem,
            "priority": issue.priority,
            "technician": issue.technician or "-",
            "reportedDate": issue.reported_date.strftime("%Y-%m-%d"),
        })
    
    return Response({"issues": issues})


@api_view(["POST"])
def report_issue(request):
    """Reporta una nueva incidencia"""
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    payload = request.data or {}
    
    room = payload.get("room", "").strip()
    problem = payload.get("problem", "").strip()
    priority = payload.get("priority", "Media")
    technician = payload.get("technician", "").strip() or None
    
    if not room or not problem:
        return Response({"error": "Habitación y problema son requeridos"}, status=status.HTTP_400_BAD_REQUEST)
    
    issue = MaintenanceIssue.objects.create(
        room=room,
        problem=problem,
        priority=priority,
        technician=technician,
    )
    
    # Enviar notificación WebSocket (solo a otros usuarios, no al que la creó)
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            user_name = request.firebase_user.get('email', 'Usuario').split('@')[0]
            user_uid = request.firebase_user.get('uid')
            
            print(f"🔔 Enviando notificación de incidencia - Usuario: {user_name}, UID: {user_uid}")
            
            notification_data = {
                'type': 'general_notification',
                'title': 'Nueva Incidencia Reportada',
                'message': f'{user_name} reportó una incidencia en la habitación {room}: {problem[:50]}',
                'notification_type': 'incidence',
                'created_by_uid': str(user_uid),  # UID del usuario que creó la notificación (como string)
                'data': {
                    'id': issue.id,
                    'room': issue.room,
                    'problem': issue.problem,
                    'priority': issue.priority,
                    'reported_by': user_name,
                }
            }
            
            async_to_sync(channel_layer.group_send)(
                'presence',
                notification_data
            )
            print(f"Notificación de incidencia enviada: {notification_data}")
        else:
            print("Channel layer no disponible")
    except Exception as e:
        print(f"Error enviando notificación WebSocket de incidencia: {e}")
    
    return Response({
        "id": issue.id,
        "room": issue.room,
        "problem": issue.problem,
        "priority": issue.priority,
        "technician": issue.technician or "-",
        "reportedDate": issue.reported_date.strftime("%Y-%m-%d"),
    })


@api_view(["DELETE"])
def delete_issue(request, issue_id):
    """Elimina una incidencia"""
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        issue = MaintenanceIssue.objects.get(id=issue_id)
        room_code = issue.room
        issue.delete()
        
        return Response({
            "message": f"Incidencia de la habitación {room_code} eliminada exitosamente",
            "room": room_code
        })
    except MaintenanceIssue.DoesNotExist:
        return Response({"error": "Incidencia no encontrada"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def blocked_rooms(request):
    """Obtiene las habitaciones bloqueadas"""
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    rooms = []
    for room in BlockedRoom.objects.all():
        rooms.append({
            "id": room.id,
            "room": room.room,
            "reason": room.reason,
            "blockedUntil": room.blocked_until.strftime("%Y-%m-%d"),
            "blockedBy": room.blocked_by or "-",
        })
    
    return Response({"rooms": rooms})


@api_view(["POST"])
def block_room(request):
    """Bloquea una habitación"""
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    payload = request.data or {}
    
    room = payload.get("room", "").strip()
    reason = payload.get("reason", "").strip()
    blocked_until = payload.get("blockedUntil")
    blocked_by = payload.get("blockedBy", "").strip() or None
    
    if not room or not reason or not blocked_until:
        return Response({"error": "Habitación, razón y fecha son requeridos"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        date_obj = datetime.strptime(blocked_until, "%Y-%m-%d").date()
        
        blocked_room = BlockedRoom.objects.create(
            room=room,
            reason=reason,
            blocked_until=date_obj,
            blocked_by=blocked_by,
        )
        
        # Actualizar estado de la habitación en la tabla Room
        from reservations.models import Room
        try:
            room_obj = Room.objects.get(code=room)
            old_status = room_obj.status
            room_obj.status = 'Bloqueada'
            room_obj.save(update_fields=['status'])
            # Forzar refresh para verificar
            room_obj.refresh_from_db()
            print(f"✅ Habitación {room} actualizada: {old_status} -> {room_obj.status} (verificado en BD)")
        except Room.DoesNotExist:
            print(f"⚠️ Habitación {room} no encontrada en la tabla Room")
        except Exception as e:
            print(f"❌ Error actualizando estado de habitación {room}: {e}")
            import traceback
            traceback.print_exc()
        
        # Enviar notificación WebSocket (solo a otros usuarios, no al que la creó)
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                user_name = request.firebase_user.get('email', 'Usuario').split('@')[0]
                user_uid = request.firebase_user.get('uid')
                
                print(f"🔔 Enviando notificación de bloqueo - Usuario: {user_name}, UID: {user_uid}")
                
                notification_data = {
                    'type': 'general_notification',
                    'title': 'Habitación Bloqueada',
                    'message': f'{user_name} bloqueó la habitación {room} hasta {blocked_until}. Razón: {reason[:50]}',
                    'notification_type': 'room_blocked',
                    'created_by_uid': str(user_uid),  # UID del usuario que creó la notificación (como string)
                    'data': {
                        'id': blocked_room.id,
                        'room': blocked_room.room,
                        'reason': blocked_room.reason,
                        'blocked_until': blocked_room.blocked_until.strftime("%Y-%m-%d"),
                        'blocked_by': blocked_by or user_name,
                    }
                }
                
                async_to_sync(channel_layer.group_send)(
                    'presence',
                    notification_data
                )
                print(f"Notificación de bloqueo enviada: {notification_data}")
            else:
                print("Channel layer no disponible")
        except Exception as e:
            print(f"Error enviando notificación WebSocket de bloqueo: {e}")
        
        return Response({
            "id": blocked_room.id,
            "room": blocked_room.room,
            "reason": blocked_room.reason,
            "blockedUntil": blocked_room.blocked_until.strftime("%Y-%m-%d"),
            "blockedBy": blocked_room.blocked_by or "-",
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
def unblock_room(request, room_id):
    """Libera una habitación bloqueada"""
    if not hasattr(request, "firebase_user") or not request.firebase_user:
        return Response({"error": "Usuario no autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        blocked_room = BlockedRoom.objects.get(id=room_id)
        room_code = blocked_room.room
        blocked_room.delete()
        
        # Actualizar estado de la habitación en la tabla Room
        from reservations.models import Room, Reservation, ReservationRoom
        
        try:
            room_obj = Room.objects.get(code=room_code)
            old_status = room_obj.status
            
            # Verificar si la habitación está ocupada por una reserva en Check-in
            is_occupied = False
            checkin_reservations = Reservation.objects.filter(status='Check-in')
            for res in checkin_reservations:
                if res.room_label and str(res.room_label).strip() == room_code:
                    is_occupied = True
                    break
                for ar in res.assigned_rooms.all():
                    if str(ar.room_code).strip() == room_code:
                        is_occupied = True
                        break
                if is_occupied:
                    break
            
            if is_occupied:
                new_status = 'Ocupada'
            else:
                new_status = 'Disponible'
            
            room_obj.status = new_status
            room_obj.save(update_fields=['status'])
            # Forzar refresh para verificar
            room_obj.refresh_from_db()
            print(f"✅ Habitación {room_code} actualizada: {old_status} -> {room_obj.status} (verificado en BD)")
        except Room.DoesNotExist:
            print(f"⚠️ Habitación {room_code} no encontrada en la tabla Room")
        except Exception as e:
            print(f"❌ Error actualizando estado de habitación {room_code}: {e}")
            import traceback
            traceback.print_exc()
        
        return Response({
            "message": f"Habitación {room_code} liberada exitosamente",
            "room": room_code
        })
    except BlockedRoom.DoesNotExist:
        return Response({"error": "Habitación bloqueada no encontrada"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)