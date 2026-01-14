import os
import sys
import re
import json
import google.generativeai as genai
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from .models import ChatbotSession, ChatbotMessage
from huespedes.models import Huesped
from django.db.models import Sum, Count
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


def safe_print(message):
    """Print que maneja caracteres Unicode de forma segura para servidores con ASCII"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Convertir a ASCII ignorando caracteres no soportados
        safe_message = str(message).encode('ascii', 'ignore').decode('ascii')
        print(safe_message)


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
        safe_print(f"Error al configurar Gemini: {e}")


def lookup_documento_api(doc_type, number):
    """
    Consulta la API de Factiliza para obtener información de DNI, CE o RUC.
    Retorna un diccionario con los datos o None si falla.
    """
    try:
        doc_type = doc_type.upper()
        number = str(number).strip()
        
        if not doc_type or not number:
            return None
        
        token = getattr(settings, 'LOOKUP_API_TOKEN', None) or os.environ.get('LOOKUP_API_TOKEN', '')
        
        # URLs por defecto (Factiliza)
        if doc_type == 'DNI':
            url = f"https://api.factiliza.com/v1/dni/info/{number}"
        elif doc_type == 'RUC':
            url = f"https://api.factiliza.com/v1/ruc/info/{number}"
        elif doc_type == 'CE':
            url = f"https://api.factiliza.com/v1/cee/info/{number}"
        else:
            return None
        
        headers = {}
        if token:
            headers['Authorization'] = f"Bearer {token}"
        
        req = Request(url, headers=headers)
        with urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
            payload = json.loads(raw)
        
        success = bool(payload.get('success'))
        data = payload.get('data') or {}
        
        if not success:
            return {'error': payload.get('message') or 'Consulta fallida'}
        
        # Extraer información relevante según el tipo de documento
        if doc_type == 'DNI':
            nombre = data.get('nombre_completo') or (
                ((data.get('nombres') or '') + ' ' + (data.get('apellido_paterno') or '') + ' ' + (data.get('apellido_materno') or '')).strip()
            )
            return {
                'tipo': 'DNI',
                'numero': number,
                'nombre': nombre,
                'nombres': data.get('nombres', ''),
                'apellido_paterno': data.get('apellido_paterno', ''),
                'apellido_materno': data.get('apellido_materno', ''),
            }
        elif doc_type == 'RUC':
            return {
                'tipo': 'RUC',
                'numero': number,
                'razon_social': data.get('nombre_o_razon_social') or data.get('razon_social', ''),
                'estado': data.get('estado') or data.get('estado_del_contribuyente', ''),
                'condicion': data.get('condicion') or data.get('condicion_del_contribuyente', ''),
                'direccion': data.get('direccion_completa') or data.get('domicilio_fiscal', ''),
                'tipo_contribuyente': data.get('tipo_contribuyente', ''),
            }
        elif doc_type == 'CE':
            nombre = (
                ((data.get('nombres') or '') + ' ' + (data.get('apellido_paterno') or '') + ' ' + (data.get('apellido_materno') or '')).strip()
            )
            return {
                'tipo': 'CE',
                'numero': number,
                'nombre': nombre,
                'nombres': data.get('nombres', ''),
                'apellido_paterno': data.get('apellido_paterno', ''),
                'apellido_materno': data.get('apellido_materno', ''),
            }
        
        return data
        
    except HTTPError as e:
        safe_print(f"Error HTTP al consultar documento: {e.code}")
        return {'error': f'Error HTTP {e.code}'}
    except URLError as e:
        safe_print(f"Error de conexión al consultar documento: {e}")
        return {'error': 'No se pudo conectar al servicio de consultas'}
    except Exception as e:
        safe_print(f"Error al consultar documento: {e}")
        return {'error': str(e)}


def detectar_y_consultar_documento(message_text):
    """
    Detecta si el mensaje contiene una consulta de DNI, CE o RUC y la procesa.
    Retorna una respuesta formateada o None si no es una consulta de documento.
    """
    text = message_text.lower().strip()
    
    # Patrones para detectar consultas de documentos
    # DNI: 8 dígitos
    dni_patterns = [
        r'(?:consulta|busca|buscar|quien\s+es|informacion|info|datos)?\s*(?:del?\s+)?dni\s*[:\-]?\s*(\d{8})\b',
        r'\bdni\s*[:\-]?\s*(\d{8})\b',
        r'(?:consulta|busca|buscar|quien\s+es)\s+(\d{8})\b',
    ]
    
    # RUC: 11 dígitos
    ruc_patterns = [
        r'(?:consulta|busca|buscar|informacion|info|datos)?\s*(?:del?\s+)?ruc\s*[:\-]?\s*(\d{11})\b',
        r'\bruc\s*[:\-]?\s*(\d{11})\b',
    ]
    
    # CE: Carné de Extranjería
    ce_patterns = [
        r'(?:consulta|busca|buscar|quien\s+es|informacion|info|datos)?\s*(?:del?\s+)?(?:ce|carne\s+de\s+extranjeria|carnet\s+extranjeria)\s*[:\-]?\s*(\d{9,12})\b',
        r'\bce\s*[:\-]?\s*(\d{9,12})\b',
    ]
    
    # Buscar DNI
    for pattern in dni_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            numero = match.group(1)
            resultado = lookup_documento_api('DNI', numero)
            if resultado:
                if 'error' in resultado:
                    return f"No se pudo consultar el DNI {numero}: {resultado['error']}"
                return (
                    f"**Consulta DNI: {numero}**\n\n"
                    f"**Nombre completo:** {resultado.get('nombre', 'No disponible')}\n"
                    f"- Nombres: {resultado.get('nombres', 'N/A')}\n"
                    f"- Apellido paterno: {resultado.get('apellido_paterno', 'N/A')}\n"
                    f"- Apellido materno: {resultado.get('apellido_materno', 'N/A')}"
                )
            return f"No se encontró información para el DNI {numero}."
    
    # Buscar RUC
    for pattern in ruc_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            numero = match.group(1)
            resultado = lookup_documento_api('RUC', numero)
            if resultado:
                if 'error' in resultado:
                    return f"No se pudo consultar el RUC {numero}: {resultado['error']}"
                return (
                    f"**Consulta RUC: {numero}**\n\n"
                    f"**Razón Social:** {resultado.get('razon_social', 'No disponible')}\n"
                    f"- Estado: {resultado.get('estado', 'N/A')}\n"
                    f"- Condición: {resultado.get('condicion', 'N/A')}\n"
                    f"- Dirección: {resultado.get('direccion', 'N/A')}\n"
                    f"- Tipo: {resultado.get('tipo_contribuyente', 'N/A')}"
                )
            return f"No se encontró información para el RUC {numero}."
    
    # Buscar CE
    for pattern in ce_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            numero = match.group(1)
            resultado = lookup_documento_api('CE', numero)
            if resultado:
                if 'error' in resultado:
                    return f"No se pudo consultar el CE {numero}: {resultado['error']}"
                return (
                    f"**Consulta Carné de Extranjería: {numero}**\n\n"
                    f"**Nombre completo:** {resultado.get('nombre', 'No disponible')}\n"
                    f"- Nombres: {resultado.get('nombres', 'N/A')}\n"
                    f"- Apellido paterno: {resultado.get('apellido_paterno', 'N/A')}\n"
                    f"- Apellido materno: {resultado.get('apellido_materno', 'N/A')}"
                )
            return f"No se encontró información para el CE {numero}."
    
    # No es una consulta de documento
    return None


def get_huespedes_context():
    try:
        now = timezone.localtime()
        today = now.date()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).date()
        fmt = lambda d: d.strftime('%Y-%m-%d') if d else ''
        total_registros = Huesped.objects.count()
        registros_mes = Huesped.objects.filter(check_in__gte=current_month_start).count()
        checkins_hoy = Huesped.objects.filter(check_in=today).count()
        checkouts_hoy = Huesped.objects.filter(check_out=today).count()
        huespedes_actuales_qs = Huesped.objects.filter(check_in__lte=today, check_out__gt=today)
        huespedes_actuales = [
            {
                'nombre': h.nombres_apellidos,
                'habitacion': h.numero_habitacion,
                'check_in': fmt(h.check_in),
                'hora_entrada': h.hora_entrada.strftime('%I:%M %p') if h.hora_entrada else '',
                'check_out': fmt(h.check_out),
                'hora_salida': h.hora_salida.strftime('%I:%M %p') if h.hora_salida else ''
            }
            for h in huespedes_actuales_qs[:10]
        ]
        proximos_checkins_qs = Huesped.objects.filter(check_in__gt=today).order_by('check_in')[:10]
        proximos_checkins = [
            {
                'nombre': h.nombres_apellidos,
                'habitacion': h.numero_habitacion,
                'check_in': fmt(h.check_in),
                'hora_entrada': h.hora_entrada.strftime('%I:%M %p') if h.hora_entrada else '',
                'check_out': fmt(h.check_out),
                'hora_salida': h.hora_salida.strftime('%I:%M %p') if h.hora_salida else ''
            }
            for h in proximos_checkins_qs
        ]
        ingresos_mes = 0.0
        for h in Huesped.objects.filter(check_in__gte=current_month_start):
            try:
                ingresos_mes += float(h.total_estadia)
            except Exception:
                pass
        ingresos_hoy = 0.0
        for h in Huesped.objects.filter(check_in=today):
            try:
                ingresos_hoy += float(h.total_estadia)
            except Exception:
                pass
        por_canal = list(
            Huesped.objects.values('canal_venta').annotate(count=Count('id')).order_by('-count')
        )
        por_tipo_habitacion = list(
            Huesped.objects.values('tipo_habitacion').annotate(count=Count('id')).order_by('-count')
        )
        top_nacionalidades = list(
            Huesped.objects.values('nacionalidad').annotate(count=Count('id')).order_by('-count')[:5]
        )
        recientes = []
        for h in Huesped.objects.all().order_by('-fecha_registro')[:10]:
            try:
                total = float(h.total_estadia)
            except Exception:
                total = 0.0
            recientes.append({
                'nombre': h.nombres_apellidos,
                'documento': h.numero_documento,
                'ruc': h.numero_ruc or '',
                'habitacion': h.numero_habitacion,
                'check_in': fmt(h.check_in),
                'hora_entrada': h.hora_entrada.strftime('%I:%M %p') if h.hora_entrada else '',
                'check_out': fmt(h.check_out),
                'hora_salida': h.hora_salida.strftime('%I:%M %p') if h.hora_salida else '',
                'total_estadia': total,
                'is_day_use': h.is_day_use
            })
        return {
            'fecha_actual': now.strftime('%Y-%m-%d'),
            'hora_actual': now.strftime('%H:%M'),
            'total_registros': total_registros,
            'registros_mes': registros_mes,
            'ingresos_mes': round(ingresos_mes, 2),
            'ingresos_hoy': round(ingresos_hoy, 2),
            'checkins_hoy': checkins_hoy,
            'checkouts_hoy': checkouts_hoy,
            'huespedes_actuales': huespedes_actuales,
            'proximos_checkins': proximos_checkins,
            'por_canal': por_canal,
            'por_tipo_habitacion': por_tipo_habitacion,
            'top_nacionalidades': top_nacionalidades,
            'recientes': recientes,
        }
    except Exception as e:
        import traceback
        safe_print(f"Error en get_huespedes_context: {e}")
        safe_print(traceback.format_exc())
        return {'error': str(e), 'fecha_actual': timezone.localtime().strftime('%Y-%m-%d')}


def build_fallback_response(message_text, data):
    try:
        term = (message_text or '').lower()
        ingresos_hoy = data.get('ingresos_hoy', 0)
        ingresos_mes = data.get('ingresos_mes', 0)
        checkins_hoy = data.get('checkins_hoy', 0)
        checkouts_hoy = data.get('checkouts_hoy', 0)
        total_registros = data.get('total_registros', 0)
        huespedes_actuales = data.get('huespedes_actuales', [])
        proximos_checkins = data.get('proximos_checkins', [])
        por_canal = data.get('por_canal', [])
        por_tipo_habitacion = data.get('por_tipo_habitacion', [])
        top_nacionalidades = data.get('top_nacionalidades', [])

        def fmt_soles(v):
            try:
                return f"S/ {float(v):,.2f}"
            except Exception:
                return "S/ 0.00"

        # Respuestas especializadas por palabra clave
        if 'ingreso' in term:
            return (
                f"Ingresos: Hoy {fmt_soles(ingresos_hoy)} | Mes {fmt_soles(ingresos_mes)}."
            )
        if 'check-in' in term or 'checkin' in term or 'llegad' in term:
            if proximos_checkins:
                lines = [
                    f"- {h.get('nombre','')} Hab {h.get('habitacion','')} del {h.get('check_in','')} al {h.get('check_out','')}"
                    for h in proximos_checkins[:5]
                ]
                return "Próximos check-ins:\n" + "\n".join(lines)
            return "No hay próximos check-ins registrados."
        if 'check-out' in term or 'checkout' in term or 'salid' in term:
            return f"Check-outs hoy: {checkouts_hoy}."
        if 'actual' in term or 'ocupación' in term or 'ocupacion' in term:
            return f"Huéspedes alojados actualmente: {len(huespedes_actuales)}."
        if 'canal' in term or 'whatsapp' in term:
            if por_canal:
                canal_str = ', '.join([f"{i.get('canal_venta','')}: {i.get('count',0)}" for i in por_canal])
                return f"Distribución por canal: {canal_str}."
            return "Sin datos por canal."

        # Resumen general si no coincide nada especifico
        seccion_actuales = (
            "Huespedes actuales:\n" +
            ("\n".join([f"- {h.get('nombre','')} Hab {h.get('habitacion','')} - Entrada: {h.get('check_in','')}{' ' + h.get('hora_entrada','') if h.get('hora_entrada') else ''} - Sale: {h.get('check_out','')}{' ' + h.get('hora_salida','') if h.get('hora_salida') else ''}" for h in huespedes_actuales[:5]])
             if huespedes_actuales else "Sin huespedes actualmente")
        )
        seccion_proximos = (
            "Proximos check-ins:\n" +
            ("\n".join([f"- {h.get('nombre','')} Hab {h.get('habitacion','')} - {h.get('check_in','')}{' ' + h.get('hora_entrada','') if h.get('hora_entrada') else ''} al {h.get('check_out','')}{' ' + h.get('hora_salida','') if h.get('hora_salida') else ''}" for h in proximos_checkins[:5]])
             if proximos_checkins else "Sin proximos check-ins")
        )
        canal_str = ', '.join([f"{i.get('canal_venta','')}: {i.get('count',0)}" for i in por_canal]) if por_canal else 'Sin datos'
        tipo_str = ', '.join([f"{i.get('tipo_habitacion','')}: {i.get('count',0)}" for i in por_tipo_habitacion]) if por_tipo_habitacion else 'Sin datos'
        nac_str = ', '.join([f"{i.get('nacionalidad','')}: {i.get('count',0)}" for i in top_nacionalidades]) if top_nacionalidades else 'Sin datos'

        return (
            f"Resumen:\n"
            f"- Total registros: {total_registros}\n"
            f"- Check-ins hoy: {checkins_hoy} | Check-outs hoy: {checkouts_hoy}\n"
            f"- Ingresos hoy: {fmt_soles(ingresos_hoy)} | Mes: {fmt_soles(ingresos_mes)}\n\n"
            f"{seccion_actuales}\n\n{seccion_proximos}\n\n"
            f"Distribución: Canal [{canal_str}] | Tipo habitación [{tipo_str}] | Top nacionalidades [{nac_str}]"
        )
    except Exception:
        return "El servicio de IA no está disponible temporalmente. Intenta de nuevo más tarde."

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
            
            # Verificar si es una consulta de DNI, CE o RUC
            documento_response = detectar_y_consultar_documento(message_text)
            if documento_response:
                # Es una consulta de documento, responder directamente
                assistant_message = ChatbotMessage.objects.create(
                    session=session,
                    role='assistant',
                    content=documento_response
                )
                return Response({
                    'message': documento_response,
                    'timestamp': assistant_message.timestamp.isoformat(),
                    'session_id': session_id
                })
            
            # Obtener historial de mensajes (excluyendo el mensaje actual del usuario)
            # IMPORTANTE: hacer exclude ANTES del slice
            previous_messages = ChatbotMessage.objects.filter(
                session=session
            ).exclude(id=user_message.id).order_by('timestamp')[:20]  # Últimos 20 mensajes (sin el actual)
            
            dashboard_data = get_huespedes_context()
            
            # Crear prompt del sistema con contexto completo
            import json
            
            # Formatear datos para el prompt
            huespedes = dashboard_data.get('huespedes_actuales', [])
            huespedes_str = '\n'.join([f"  - {h['nombre']} - Hab {h['habitacion']} - Entrada: {h['check_in']}{' ' + h['hora_entrada'] if h.get('hora_entrada') else ''} - Sale: {h['check_out']}{' ' + h['hora_salida'] if h.get('hora_salida') else ''}" for h in huespedes[:5]]) if huespedes else '  Sin huéspedes actualmente'
            proximos = dashboard_data.get('proximos_checkins', [])
            proximos_str = '\n'.join([f"  - {h['nombre']} - Hab {h['habitacion']} - {h['check_in']}{' ' + h['hora_entrada'] if h.get('hora_entrada') else ''} al {h['check_out']}{' ' + h['hora_salida'] if h.get('hora_salida') else ''}" for h in proximos[:5]]) if proximos else '  Sin próximos check-ins'
            recientes = dashboard_data.get('recientes', [])
            recientes_str = '\n'.join([f"  - {r['nombre']} ({r['documento']}) - Hab {r['habitacion']} - {r['check_in']}{' ' + r['hora_entrada'] if r.get('hora_entrada') else ''} al {r['check_out']}{' ' + r['hora_salida'] if r.get('hora_salida') else ''}{' [DAY USE]' if r.get('is_day_use') else ''} - Total: S/ {r['total_estadia']:,.2f}" for r in recientes]) if recientes else '  Sin datos recientes'
            por_canal = dashboard_data.get('por_canal', [])
            por_canal_str = ', '.join([f"{i['canal_venta']}: {i['count']}" for i in por_canal]) if por_canal else 'Sin datos'
            por_tipo = dashboard_data.get('por_tipo_habitacion', [])
            por_tipo_str = ', '.join([f"{i['tipo_habitacion']}: {i['count']}" for i in por_tipo]) if por_tipo else 'Sin datos'
            top_nac = dashboard_data.get('top_nacionalidades', [])
            top_nac_str = ', '.join([f"{i['nacionalidad']}: {i['count']}" for i in top_nac]) if top_nac else 'Sin datos'
            system_prompt = f"""Eres un asistente del Hotel Plaza Trujillo especializado en informacion de PASAJEROS.

[FECHA Y HORA] {dashboard_data.get('fecha_actual', 'N/A')} {dashboard_data.get('hora_actual', 'N/A')}

[RESUMEN DE PASAJEROS]
- Total de registros: {dashboard_data.get('total_registros', 0)}
- Registros del mes: {dashboard_data.get('registros_mes', 0)}
- Check-ins hoy: {dashboard_data.get('checkins_hoy', 0)}
- Check-outs hoy: {dashboard_data.get('checkouts_hoy', 0)}
- Ingresos hoy: S/ {dashboard_data.get('ingresos_hoy', 0):,.2f}
- Ingresos del mes: S/ {dashboard_data.get('ingresos_mes', 0):,.2f}

[HUESPEDES ACTUALES]
{huespedes_str}

[PROXIMOS CHECK-INS]
{proximos_str}

[PASAJEROS RECIENTES]
{recientes_str}

[DISTRIBUCION]
- Por canal: {por_canal_str}
- Por tipo de habitacion: {por_tipo_str}
- Top nacionalidades: {top_nac_str}

            Instrucciones:
            - Responde SOLO sobre lo que el usuario pregunta.
            - No menciones canales de venta (incluido WhatsApp) ni su ausencia a menos que el usuario lo solicite explicitamente.
            - Si faltan datos, indicalo unicamente respecto al tema preguntado (no generalices ni agregues temas no solicitados).
            - Usa los datos anteriores para responder de forma precisa.
            - Formatea montos como S/ 1,234.56.
            - Responde en espanol y con claridad.
            - Si no hay datos suficientes sobre el tema preguntado, indicalo explicitamente sin anadir informacion irrelevante.
            - Puedes indicar al usuario que puede consultar informacion de DNI (8 digitos), RUC (11 digitos) o Carne de Extranjeria (CE) escribiendo por ejemplo: "DNI 12345678" o "RUC 12345678901".
            - Si el usuario pregunta como consultar un documento, indicale que puede escribir "DNI" seguido del numero, "RUC" seguido del numero, o "CE" seguido del numero."""
            
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
                    safe_print(f"[OK] Modelo '{model_name}' inicializado correctamente")
                    break
                except Exception as e:
                    error_msg = str(e)
                    model_errors.append(f"{model_name_attempt}: {error_msg}")
                    safe_print(f"[WARN] Modelo '{model_name_attempt}' no disponible: {error_msg}")
                    continue
            
            if model is None:
                # Fallback a respuesta basada en datos locales
                assistant_response = build_fallback_response(message_text, dashboard_data)
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
                        safe_print(f"Error con historial, intentando sin historial: {chat_error}")
                        response = model.generate_content(full_message)
                else:
                    # Primera interacción, generar contenido directamente
                    response = model.generate_content(full_message)
            except Exception as gen_error:
                # Fallback a respuesta basada en datos locales
                assistant_response = build_fallback_response(message_text, dashboard_data)
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
                    safe_print(f"Error al extraer texto de respuesta: {extract_error}")
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
        safe_print(f"Error en chatbot: {str(e)}")
        safe_print(f"Traceback: {error_trace}")
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
