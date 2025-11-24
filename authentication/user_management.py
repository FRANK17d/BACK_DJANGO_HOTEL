import firebase_admin
from firebase_admin import auth
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from .models import UserProfile
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
import os

@api_view(['POST'])
def create_user_with_role(request):
    """
    Endpoint para que el administrador cree usuarios y les asigne roles
    Solo accesible por administradores
    """
    # Verificar que el usuario sea administrador
    if not hasattr(request, 'firebase_user_role') or request.firebase_user_role != 'admin':
        return Response({
            'error': 'Acceso denegado. Se requiere rol de administrador.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        email = request.data.get('email')
        password = request.data.get('password')
        role = request.data.get('role')
        display_name = request.data.get('display_name', '')
        salary = request.data.get('salary', '')
        entry_date = request.data.get('entry_date', '')
        attendance = request.data.get('attendance', '')
        
        # Validar datos
        if not email or not password or not role:
            return Response({
                'error': 'Email, password y role son requeridos'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if role not in ['admin', 'receptionist', 'housekeeping']:
            return Response({
                'error': 'Role debe ser "admin", "receptionist" o "housekeeping"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear usuario en Firebase
        user_record = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=False  # El usuario puede verificar su email después
        )
        
        # Asignar custom claim (rol)
        auth.set_custom_user_claims(user_record.uid, {'role': role})
        
        # Guardar datos adicionales en MySQL
        UserProfile.objects.create(
            firebase_uid=user_record.uid,
            email=email,
            display_name=display_name,
            role=role,
            salary=salary,
            entry_date=entry_date if entry_date else None,
            attendance=attendance
        )
        # Enviar email con credenciales al nuevo usuario
        email_sent = False
        try:
            subject = 'Credenciales de acceso - Hotel Plaza Trujillo'
            login_url = os.environ.get('FRONT_LOGIN_URL', '')

            text_lines = [
                f'Hola {display_name or ""},',
                '',
                'Tu cuenta ha sido creada exitosamente.',
                f'Email: {email}',
                f'Contraseña: {password}',
            ]
            if login_url:
                text_lines += ['', f'Puedes iniciar sesión en: {login_url}']
            text_lines += [
                '',
                'Por seguridad, te recomendamos cambiar tu contraseña en tu primer inicio de sesión.',
                '',
                'Saludos,',
                'Hotel Plaza Trujillo'
            ]
            text_content = '\n'.join(text_lines)

            html_content = f"""
            <div style="font-family: Inter, Arial, sans-serif; background:#0f172a; padding:32px;">
              <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:640px;margin:0 auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;">
                <tr>
                  <td style="padding:24px;">
                    <h1 style="margin:0 0 8px 0; font-size:22px; color:#0f172a;">Bienvenido(a) a Hotel Plaza Trujillo</h1>
                    <p style="margin:0 0 16px 0; font-size:14px; color:#334155;">Tu cuenta ha sido creada. Aquí están tus credenciales de acceso:</p>
                    <div style="margin:0 0 16px 0; padding:16px; background:#fff7ed; border:1px solid #fdba74; border-radius:12px;">
                      <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                        <tr>
                          <td style="font-weight:600;color:#9a3412;width:140px;font-size:14px;">Nombre</td>
                          <td style="color:#0f172a;font-size:14px;">{display_name or ''}</td>
                        </tr>
                        <tr>
                          <td style="font-weight:600;color:#9a3412;width:140px;font-size:14px;">Email</td>
                          <td style="color:#0f172a;font-size:14px;">{email}</td>
                        </tr>
                        <tr>
                          <td style="font-weight:600;color:#9a3412;width:140px;font-size:14px;">Contraseña</td>
                          <td style="color:#0f172a;font-size:14px;font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", \"Courier New\", monospace;">{password}</td>
                        </tr>
                      </table>
                    </div>
                    <div style="margin-top:12px; padding:16px; background:#f8fafc; border:1px solid #e5e7eb; border-radius:12px;">
                      <p style="margin:0 0 8px 0; font-size:12px; color:#0f172a; font-weight:600;">Instrucciones</p>
                      <ul style="margin:0; padding-left:18px; color:#334155; font-size:12px;">
                        <li>Esta es tu contraseña inicial. Cámbiala tras el primer inicio de sesión.</li>
                        <li>Puedes iniciar sesión inmediatamente con estas credenciales.</li>
                        <li>Guarda estas credenciales de forma segura.</li>
                      </ul>
                    </div>
                    {f'<p style="margin-top:16px;"><a href="{login_url}" style="display:inline-block;padding:10px 16px;background:#ea580c;color:#ffffff;border-radius:10px;text-decoration:none;font-size:14px;">Ir al acceso</a></p>' if login_url else ''}
                    <p style="margin-top:16px; font-size:12px; color:#64748b;">Hotel Plaza Trujillo</p>
                  </td>
                </tr>
              </table>
            </div>
            """

            email_message = EmailMultiAlternatives(
                subject,
                text_content,
                getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                [email],
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send(fail_silently=False)
            email_sent = True
        except Exception as e:
            email_sent = False
            email_error = str(e)

        resp = {
            'message': 'Usuario creado exitosamente. Puede iniciar sesión inmediatamente con las credenciales proporcionadas.',
            'user_id': user_record.uid,
            'email': user_record.email,
            'role': role,
            'display_name': user_record.display_name,
            'password': password,
            'email_sent': email_sent
        }
        if not email_sent:
            resp['email_error'] = locals().get('email_error', 'EMAIL_SEND_FAILED')
        return Response(resp)
        
    except auth.EmailAlreadyExistsError:
        return Response({
            'error': 'El email ya está registrado'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': f'Error creando usuario: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def list_users(request):
    """
    Listar todos los usuarios (solo administradores)
    """
    if not hasattr(request, 'firebase_user_role') or request.firebase_user_role not in ['admin']:
        return Response({
            'error': 'Acceso denegado. Se requiere rol de administrador.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Listar usuarios de Firebase
        page = auth.list_users()
        
        # Obtener todos los UIDs de Firebase
        firebase_uids = [user.uid for user in page.users]
        
        # Obtener todos los perfiles de MySQL en UNA SOLA consulta (optimización)
        profiles_dict = {}
        if firebase_uids:
            profiles = UserProfile.objects.filter(firebase_uid__in=firebase_uids)
            profiles_dict = {profile.firebase_uid: profile for profile in profiles}
        
        # Construir lista de usuarios
        users = []
        for user in page.users:
            # Obtener custom claims
            custom_claims = user.custom_claims or {}
            role = custom_claims.get('role', 'sin_rol')
            
            # Buscar perfil en el diccionario (sin consultas adicionales)
            profile = profiles_dict.get(user.uid)
            if profile:
                salary = profile.salary or ''
                entry_date = profile.entry_date.isoformat() if profile.entry_date else ''
                attendance = profile.attendance or ''
                profile_photo_url = profile.profile_photo_url or ''
            else:
                salary = ''
                entry_date = ''
                attendance = ''
                profile_photo_url = ''
            
            users.append({
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name,
                'role': role,
                'email_verified': user.email_verified,
                'disabled': user.disabled,
                'creation_time': user.user_metadata.creation_timestamp,
                'salary': salary,
                'entry_date': entry_date,
                'attendance': attendance,
                'profile_photo_url': profile_photo_url
            })
        
        return Response({
            'users': users,
            'total': len(users)
        })
        
    except Exception as e:
        print(f"Error en list_users: {str(e)}")
        return Response({
            'error': f'Error listando usuarios: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
def update_user_role(request, uid):
    """
    Cambiar el rol y datos adicionales de un usuario existente
    """
    if not hasattr(request, 'firebase_user_role') or request.firebase_user_role != 'admin':
        return Response({
            'error': 'Acceso denegado. Se requiere rol de administrador.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        new_role = request.data.get('role')
        salary = request.data.get('salary')
        entry_date = request.data.get('entry_date')
        attendance = request.data.get('attendance')
        
        if new_role and new_role not in ['admin', 'receptionist', 'housekeeping']:
            return Response({
                'error': 'Role debe ser "admin", "receptionist" o "housekeeping"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Actualizar custom claims si se proporciona rol
        if new_role:
            auth.set_custom_user_claims(uid, {'role': new_role})
        
        # Actualizar datos adicionales en MySQL
        try:
            profile = UserProfile.objects.get(firebase_uid=uid)
            if new_role:
                profile.role = new_role
            if salary is not None:
                profile.salary = salary
            if entry_date is not None:
                profile.entry_date = entry_date if entry_date else None
            if attendance is not None:
                profile.attendance = attendance
            profile.save()
        except UserProfile.DoesNotExist:
            # Si no existe el perfil, crearlo
            UserProfile.objects.create(
                firebase_uid=uid,
                email=auth.get_user(uid).email,
                display_name=auth.get_user(uid).display_name,
                role=new_role or 'receptionist',
                salary=salary or '',
                entry_date=entry_date if entry_date else None,
                attendance=attendance or ''
            )
        
        return Response({
            'message': 'Usuario actualizado exitosamente',
            'user_id': uid
        })
        
    except auth.UserNotFoundError:
        return Response({
            'error': 'Usuario no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Error actualizando usuario: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
def delete_user(request, uid):
    """
    Eliminar un usuario
    """
    if not hasattr(request, 'firebase_user_role') or request.firebase_user_role != 'admin':
        return Response({
            'error': 'Acceso denegado. Se requiere rol de administrador.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Eliminar de Firebase Auth
        auth.delete_user(uid)
        
        # Eliminar de MySQL
        try:
            profile = UserProfile.objects.get(firebase_uid=uid)
            profile.delete()
        except UserProfile.DoesNotExist:
            pass  # No hay problema si no existe
        
        return Response({
            'message': 'Usuario eliminado exitosamente'
        })
        
    except auth.UserNotFoundError:
        return Response({
            'error': 'Usuario no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Error eliminando usuario: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'PATCH'])
def update_own_profile(request):
    """
    Obtener o actualizar el perfil del usuario autenticado.
    - GET: devuelve el perfil del usuario autenticado
    - PATCH: actualiza display_name y/o profile_photo_url
    """
    try:
        if not hasattr(request, 'firebase_user') or not request.firebase_user:
            return Response({
                'error': 'Usuario no autenticado'
            }, status=status.HTTP_401_UNAUTHORIZED)

        uid = request.firebase_user['uid']

        if request.method == 'GET':
            try:
                profile = UserProfile.objects.get(firebase_uid=uid)
                return Response({
                    'profile': {
                        'uid': uid,
                        'email': profile.email,
                        'display_name': profile.display_name,
                        'role': profile.role,
                        'profile_photo_url': profile.profile_photo_url
                    }
                })
            except UserProfile.DoesNotExist:
                user_record = auth.get_user(uid)
                return Response({
                    'profile': {
                        'uid': uid,
                        'email': user_record.email,
                        'display_name': user_record.display_name,
                        'role': 'receptionist',
                        'profile_photo_url': ''
                    }
                })

        display_name = request.data.get('display_name')
        profile_photo_url = request.data.get('profile_photo_url')

        if display_name:
            auth.update_user(uid, display_name=display_name)

        try:
            profile = UserProfile.objects.get(firebase_uid=uid)
            if display_name:
                profile.display_name = display_name
            if profile_photo_url is not None:
                profile.profile_photo_url = profile_photo_url
            profile.save()
        except UserProfile.DoesNotExist:
            user_record = auth.get_user(uid)
            UserProfile.objects.create(
                firebase_uid=uid,
                email=user_record.email,
                display_name=display_name or user_record.display_name,
                role='receptionist',
                profile_photo_url=profile_photo_url or ''
            )

        updated_profile = UserProfile.objects.get(firebase_uid=uid)

        return Response({
            'message': 'Perfil actualizado exitosamente',
            'profile': {
                'uid': uid,
                'email': updated_profile.email,
                'display_name': updated_profile.display_name,
                'role': updated_profile.role,
                'profile_photo_url': updated_profile.profile_photo_url
            }
        })

    except Exception as e:
        return Response({
            'error': f'Error actualizando perfil: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






