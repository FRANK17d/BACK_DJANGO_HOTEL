import os
import google.generativeai as genai
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from .models import ChatbotSession, ChatbotMessage
from dashboard.views import (
    dashboard_metrics,
    monthly_revenue_chart,
    payment_methods_chart,
    occupancy_weekly_chart,
    today_checkins_checkouts,
    recent_reservations,
    statistics_chart
)
from reservations.models import Reservation
from cajacobros.models import Payment
from django.db.models import Sum, Count
from datetime import datetime, timedelta
from decimal import Decimal


# Configurar Gemini - obtener desde settings o variable de entorno
def get_gemini_api_key():
    """Obtiene la API key de Gemini de settings o variable de entorno"""
    try:
        api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
        return api_key
    except:
        return os.environ.get('GEMINI_API_KEY', '')

# Configurar Gemini al inicio
GEMINI_API_KEY = get_gemini_api_key()
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Error al configurar Gemini: {e}")


def get_dashboard_context():
    """Obtiene datos completos del hotel para el contexto del chatbot"""
    try:
        from reservations.models import Room
        
        now = timezone.localtime()
        today = now.date()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        week_start = today - timedelta(days=today.weekday())
        
        # ========== INGRESOS ==========
        # Ingresos del mes actual
        monthly_revenue = Payment.objects.filter(
            created_at__gte=current_month_start,
            status='Completado'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Ingresos del mes anterior
        last_month_revenue = Payment.objects.filter(
            created_at__gte=last_month_start,
            created_at__lt=current_month_start,
            status='Completado'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Ingresos de hoy
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_revenue = Payment.objects.filter(
            created_at__gte=today_start,
            status='Completado'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Ingresos de la semana
        weekly_revenue = Payment.objects.filter(
            created_at__gte=week_start,
            status='Completado'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Pagos por método
        payment_methods = Payment.objects.filter(
            created_at__gte=current_month_start,
            status='Completado'
        ).values('method').annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        methods_summary = {p['method']: {'total': float(p['total']), 'count': p['count']} for p in payment_methods}
        
        # ========== HABITACIONES ==========
        total_rooms = Room.objects.count()
        
        # Habitaciones ocupadas - basado en room_label de reservas activas
        occupied_room_labels = Reservation.objects.filter(
            check_in__lte=today,
            check_out__gt=today,
            status__in=['Confirmada', 'Check-in']
        ).values_list('room_label', flat=True)
        
        # Contar habitaciones únicas ocupadas
        occupied_room_codes = set()
        for label in occupied_room_labels:
            # room_label puede ser "101" o "101, 102" para múltiples habitaciones
            codes = [c.strip() for c in label.split(',')]
            occupied_room_codes.update(codes)
        
        occupied_rooms = Room.objects.filter(code__in=occupied_room_codes).count()
        available_rooms = total_rooms - occupied_rooms
        occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
        
        # Detalle de habitaciones
        rooms_detail = []
        for room in Room.objects.all()[:20]:  # Limitar a 20 para no sobrecargar
            is_occupied = room.code in occupied_room_codes
            rooms_detail.append({
                'numero': room.code,
                'tipo': room.type or 'Estándar',
                'piso': room.floor,
                'estado': 'Ocupada' if is_occupied else room.status
            })
        
        # ========== RESERVAS ==========
        # Reservas activas hoy
        active_reservations = Reservation.objects.filter(
            check_in__lte=today,
            check_out__gte=today,
            status__in=['Confirmada', 'Check-in']
        ).count()
        
        # Check-ins de hoy
        today_checkins = Reservation.objects.filter(
            check_in=today
        ).count()
        
        # Check-outs de hoy
        today_checkouts = Reservation.objects.filter(
            check_out=today
        ).count()
        
        # Reservas pendientes (futuras)
        pending_reservations = Reservation.objects.filter(
            check_in__gt=today,
            status='Confirmada'
        ).count()
        
        # Reservas del mes
        monthly_reservations = Reservation.objects.filter(
            created_at__gte=current_month_start
        ).count()
        
        # Reservas canceladas del mes
        cancelled_reservations = Reservation.objects.filter(
            created_at__gte=current_month_start,
            status='Cancelada'
        ).count()
        
        # Próximas reservas (lista)
        upcoming_reservations = []
        for res in Reservation.objects.filter(
            check_in__gte=today,
            status='Confirmada'
        ).order_by('check_in')[:10]:
            upcoming_reservations.append({
                'codigo': res.reservation_id,
                'huesped': res.guest_name,
                'habitacion': res.room_label or 'Sin asignar',
                'check_in': res.check_in.strftime('%Y-%m-%d'),
                'check_out': res.check_out.strftime('%Y-%m-%d'),
                'monto': float(res.total_amount) if res.total_amount else 0
            })
        
        # Huéspedes actuales
        current_guests = []
        for res in Reservation.objects.filter(
            check_in__lte=today,
            check_out__gte=today,
            status__in=['Confirmada', 'Check-in']
        )[:10]:
            current_guests.append({
                'nombre': res.guest_name,
                'habitacion': res.room_label or 'Sin asignar',
                'check_out': res.check_out.strftime('%Y-%m-%d')
            })
        
        # ========== ESTADÍSTICAS ==========
        # Total de reservas históricas
        total_reservations_ever = Reservation.objects.count()
        
        # Pagos recientes
        recent_payments = []
        for pay in Payment.objects.filter(status='Completado').order_by('-created_at')[:5]:
            recent_payments.append({
                'monto': float(pay.amount),
                'metodo': pay.method,
                'huesped': pay.guest_name,
                'fecha': pay.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return {
            'fecha_actual': now.strftime('%Y-%m-%d'),
            'hora_actual': now.strftime('%H:%M'),
            # Ingresos
            'ingresos_mes': float(monthly_revenue),
            'ingresos_mes_anterior': float(last_month_revenue),
            'ingresos_hoy': float(today_revenue),
            'ingresos_semana': float(weekly_revenue),
            'pagos_por_metodo': methods_summary,
            # Habitaciones
            'total_habitaciones': total_rooms,
            'habitaciones_ocupadas': occupied_rooms,
            'habitaciones_disponibles': available_rooms,
            'tasa_ocupacion': round(occupancy_rate, 1),
            'detalle_habitaciones': rooms_detail,
            # Reservas
            'reservas_activas': active_reservations,
            'checkins_hoy': today_checkins,
            'checkouts_hoy': today_checkouts,
            'reservas_pendientes': pending_reservations,
            'reservas_mes': monthly_reservations,
            'reservas_canceladas_mes': cancelled_reservations,
            'proximas_reservas': upcoming_reservations,
            'huespedes_actuales': current_guests,
            # Estadísticas
            'total_reservas_historico': total_reservations_ever,
            'pagos_recientes': recent_payments,
        }
    except Exception as e:
        import traceback
        print(f"Error en get_dashboard_context: {e}")
        print(traceback.format_exc())
        return {'error': str(e), 'fecha_actual': timezone.localtime().strftime('%Y-%m-%d')}


@api_view(['POST'])
def process_message(request):
    """Procesa un mensaje del usuario usando Gemini"""
    if not hasattr(request, 'firebase_user') or not request.firebase_user:
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Verificar API key (puede haber cambiado desde el inicio)
    current_api_key = get_gemini_api_key()
    if not current_api_key:
        return Response({
            'error': 'API key de Gemini no configurada',
            'message': 'Lo siento, el servicio de IA no está disponible en este momento. Por favor, configura la API key de Gemini en las variables de entorno o en settings.py'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    # Configurar Gemini si no está configurado o si la key cambió
    if not GEMINI_API_KEY or GEMINI_API_KEY != current_api_key:
        try:
            genai.configure(api_key=current_api_key)
        except Exception as e:
            return Response({
                'error': f'Error al configurar Gemini: {str(e)}',
                'message': 'Error al inicializar el servicio de IA. Por favor, verifica la configuración.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    user_email = request.firebase_user.get('email', 'unknown')
    message_text = request.data.get('message', '').strip()
    session_id = request.data.get('session_id', f"session_{timezone.now().timestamp()}_{user_email}")
    
    if not message_text:
        return Response({'error': 'Mensaje vacío'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            # Obtener o crear sesión
            session, created = ChatbotSession.objects.get_or_create(
                session_id=session_id,
                defaults={'user_email': user_email}
            )
            if not created:
                session.user_email = user_email
                session.save()
            
            # Guardar mensaje del usuario
            user_message = ChatbotMessage.objects.create(
                session=session,
                role='user',
                content=message_text
            )
            
            # Obtener historial de mensajes (excluyendo el mensaje actual del usuario)
            # IMPORTANTE: hacer exclude ANTES del slice
            previous_messages = ChatbotMessage.objects.filter(
                session=session
            ).exclude(id=user_message.id).order_by('timestamp')[:20]  # Últimos 20 mensajes (sin el actual)
            
            # Obtener contexto del dashboard
            dashboard_data = get_dashboard_context()
            
            # Crear prompt del sistema con contexto completo
            import json
            
            # Formatear datos para el prompt
            metodos_pago = dashboard_data.get('pagos_por_metodo', {})
            metodos_str = ', '.join([f"{m}: S/{d['total']:,.2f} ({d['count']} pagos)" for m, d in metodos_pago.items()]) if metodos_pago else 'Sin datos'
            
            proximas = dashboard_data.get('proximas_reservas', [])
            proximas_str = '\n'.join([f"  - {r['codigo']}: {r['huesped']} - Hab {r['habitacion']} - {r['check_in']} al {r['check_out']}" for r in proximas[:5]]) if proximas else '  Sin reservas próximas'
            
            huespedes = dashboard_data.get('huespedes_actuales', [])
            huespedes_str = '\n'.join([f"  - {h['nombre']} - Hab {h['habitacion']} - Sale: {h['check_out']}" for h in huespedes[:5]]) if huespedes else '  Sin huéspedes actualmente'
            
            habitaciones = dashboard_data.get('detalle_habitaciones', [])
            hab_disponibles = [h for h in habitaciones if h['estado'] == 'Disponible']
            hab_ocupadas = [h for h in habitaciones if h['estado'] == 'Ocupada']
            
            system_prompt = f"""Eres un asistente virtual inteligente del Hotel Plaza Trujillo. 
Tu función es ayudar al personal del hotel con información PRECISA y ACTUALIZADA sobre operaciones, estadísticas y gestión.

═══════════════════════════════════════════════════════════════
📅 FECHA Y HORA ACTUAL: {dashboard_data.get('fecha_actual', 'N/A')} a las {dashboard_data.get('hora_actual', 'N/A')}
═══════════════════════════════════════════════════════════════

💰 FINANZAS:
- Ingresos de HOY: S/ {dashboard_data.get('ingresos_hoy', 0):,.2f}
- Ingresos de la SEMANA: S/ {dashboard_data.get('ingresos_semana', 0):,.2f}
- Ingresos del MES ACTUAL: S/ {dashboard_data.get('ingresos_mes', 0):,.2f}
- Ingresos del MES ANTERIOR: S/ {dashboard_data.get('ingresos_mes_anterior', 0):,.2f}
- Pagos por método (este mes): {metodos_str}

🏨 HABITACIONES:
- Total de habitaciones: {dashboard_data.get('total_habitaciones', 0)}
- Ocupadas: {dashboard_data.get('habitaciones_ocupadas', 0)}
- Disponibles: {dashboard_data.get('habitaciones_disponibles', 0)}
- Tasa de ocupación: {dashboard_data.get('tasa_ocupacion', 0)}%

📋 RESERVAS:
- Reservas activas (huéspedes actuales): {dashboard_data.get('reservas_activas', 0)}
- Check-ins programados HOY: {dashboard_data.get('checkins_hoy', 0)}
- Check-outs programados HOY: {dashboard_data.get('checkouts_hoy', 0)}
- Reservas pendientes (futuras): {dashboard_data.get('reservas_pendientes', 0)}
- Reservas creadas este mes: {dashboard_data.get('reservas_mes', 0)}
- Reservas canceladas este mes: {dashboard_data.get('reservas_canceladas_mes', 0)}
- Total histórico de reservas: {dashboard_data.get('total_reservas_historico', 0)}

👥 HUÉSPEDES ACTUALES EN EL HOTEL:
{huespedes_str}

📅 PRÓXIMAS RESERVAS:
{proximas_str}

═══════════════════════════════════════════════════════════════

INSTRUCCIONES:
- Responde de manera amigable, profesional y concisa
- USA SIEMPRE los datos proporcionados arriba para responder con precisión
- Formatea números y montos claramente (ej: S/ 1,234.56)
- Siempre responde en español
- Si te preguntan algo que no está en los datos, indica que no tienes esa información específica
- Sé proactivo y ofrece información útil relacionada con las preguntas"""
            
            # Construir historial para Gemini
            history = []
            for msg in previous_messages:
                # Convertir 'assistant' a 'model' para Gemini
                role = 'model' if msg.role == 'assistant' else 'user'
                history.append({
                    'role': role,
                    'parts': [msg.content]
                })
            
            # Configurar modelo de Gemini
            # Intentar usar 'gemini-2.5-flash' primero, luego otros modelos como fallback
            model = None
            model_name = None
            model_errors = []
            
            # Lista de modelos a intentar en orden (gemini-2.5-flash primero)
            models_to_try = [
                'gemini-2.5-flash',
                'gemini-2.5-flash-exp',
                'gemini-2.0-flash-exp',
                'gemini-1.5-flash',
                'gemini-1.5-pro',
                'gemini-pro'
            ]
            
            for model_name_attempt in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name_attempt)
                    model_name = model_name_attempt
                    print(f"✅ Modelo '{model_name}' inicializado correctamente")
                    break
                except Exception as e:
                    error_msg = str(e)
                    model_errors.append(f"{model_name_attempt}: {error_msg}")
                    print(f"⚠️  Modelo '{model_name_attempt}' no disponible: {error_msg}")
                    continue
            
            if model is None:
                return Response({
                    'error': f'No se pudo inicializar ningún modelo. Errores: {"; ".join(model_errors)}',
                    'message': 'Error al inicializar el modelo de IA. Por favor, verifica tu API key de Gemini y que tengas acceso a los modelos.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Construir el mensaje completo con contexto del sistema
            full_message = f"{system_prompt}\n\nUsuario: {message_text}"
            
            # Generar respuesta
            response = None
            try:
                # Si hay historial, intentar usar chat con historial
                if history and len(history) > 0:
                    try:
                        chat = model.start_chat(history=history)
                        response = chat.send_message(full_message)
                    except Exception as chat_error:
                        # Si falla con historial, intentar sin historial
                        print(f"Error con historial, intentando sin historial: {chat_error}")
                        response = model.generate_content(full_message)
                else:
                    # Primera interacción, generar contenido directamente
                    response = model.generate_content(full_message)
            except Exception as gen_error:
                error_msg = str(gen_error)
                print(f"Error al generar respuesta con {model_name}: {error_msg}")
                return Response({
                    'error': f'Error al generar respuesta: {error_msg}',
                    'message': 'Error al procesar tu mensaje. Por favor, verifica tu API key de Gemini e inténtalo de nuevo.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Extraer el texto de la respuesta
            assistant_response = None
            try:
                assistant_response = response.text
            except AttributeError:
                # Si response no tiene atributo text, intentar otras formas
                try:
                    if hasattr(response, 'candidates') and len(response.candidates) > 0:
                        assistant_response = response.candidates[0].content.parts[0].text
                    elif hasattr(response, 'content'):
                        if hasattr(response.content, 'parts') and len(response.content.parts) > 0:
                            assistant_response = response.content.parts[0].text
                        else:
                            assistant_response = str(response.content)
                    else:
                        assistant_response = str(response)
                except Exception as extract_error:
                    print(f"Error al extraer texto de respuesta: {extract_error}")
                    return Response({
                        'error': f'Error al procesar respuesta: {str(extract_error)}',
                        'message': 'Error al procesar la respuesta del asistente. Por favor, inténtalo de nuevo.'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if not assistant_response:
                return Response({
                    'error': 'Respuesta vacía de Gemini',
                    'message': 'El asistente no pudo generar una respuesta. Por favor, inténtalo de nuevo.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Guardar respuesta del asistente
            assistant_message = ChatbotMessage.objects.create(
                session=session,
                role='assistant',
                content=assistant_response
            )
            
            return Response({
                'message': assistant_response,
                'timestamp': assistant_message.timestamp.isoformat(),
                'session_id': session_id
            })
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error en chatbot: {str(e)}")
        print(f"Traceback: {error_trace}")
        return Response({
            'error': str(e),
            'message': 'Lo siento, ha ocurrido un error al procesar tu mensaje. Por favor, inténtalo de nuevo.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_conversation_history(request):
    """Obtiene el historial de conversaciones del usuario"""
    if not hasattr(request, 'firebase_user') or not request.firebase_user:
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    
    user_email = request.firebase_user.get('email', 'unknown')
    session_id = request.GET.get('session_id')
    
    try:
        if session_id:
            # Obtener conversación específica
            try:
                session = ChatbotSession.objects.get(session_id=session_id, user_email=user_email)
                messages = ChatbotMessage.objects.filter(session=session).order_by('timestamp')
                
                conversation = {
                    'session_id': session.session_id,
                    'created_at': session.created_at.isoformat(),
                    'messages': [
                        {
                            'role': msg.role,
                            'content': msg.content,
                            'timestamp': msg.timestamp.isoformat()
                        }
                        for msg in messages
                    ]
                }
                return Response({'conversations': [conversation]})
            except ChatbotSession.DoesNotExist:
                return Response({'conversations': []})
        else:
            # Obtener todas las conversaciones del usuario
            sessions = ChatbotSession.objects.filter(user_email=user_email).order_by('-updated_at')[:10]
            
            conversations = []
            for session in sessions:
                messages = ChatbotMessage.objects.filter(session=session).order_by('timestamp')
                conversations.append({
                    'session_id': session.session_id,
                    'created_at': session.created_at.isoformat(),
                    'updated_at': session.updated_at.isoformat(),
                    'messages': [
                        {
                            'role': msg.role,
                            'content': msg.content,
                            'timestamp': msg.timestamp.isoformat()
                        }
                        for msg in messages
                    ]
                })
            
            return Response({'conversations': conversations})
            
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def end_session(request):
    """Finaliza una sesión de chat"""
    if not hasattr(request, 'firebase_user') or not request.firebase_user:
        return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    
    session_id = request.data.get('session_id')
    if not session_id:
        return Response({'error': 'session_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        session = ChatbotSession.objects.get(session_id=session_id)
        # Por ahora solo retornamos éxito, podríamos agregar un campo 'active' si es necesario
        return Response({
            'ended': True,
            'session_id': session_id
        })
    except ChatbotSession.DoesNotExist:
        return Response({'error': 'Sesión no encontrada'}, status=status.HTTP_404_NOT_FOUND)
