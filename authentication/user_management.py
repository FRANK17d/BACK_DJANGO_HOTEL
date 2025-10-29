import firebase_admin
from firebase_admin import auth
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse

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
        role = request.data.get('role')  # 'receptionist' o 'housekeeping'
        display_name = request.data.get('display_name', '')
        
        # Validar datos
        if not email or not password or not role:
            return Response({
                'error': 'Email, password y role son requeridos'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if role not in ['receptionist', 'housekeeping']:
            return Response({
                'error': 'Role debe ser "receptionist" o "housekeeping"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear usuario en Firebase
        user_record = auth.create_user(
            email=email,
            password=password,
            display_name=display_name
        )
        
        # Asignar custom claim (rol)
        auth.set_custom_user_claims(user_record.uid, {'role': role})
        
        return Response({
            'message': 'Usuario creado exitosamente',
            'user_id': user_record.uid,
            'email': user_record.email,
            'role': role,
            'display_name': user_record.display_name
        })
        
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
    if not hasattr(request, 'firebase_user_role') or request.firebase_user_role != 'admin':
        return Response({
            'error': 'Acceso denegado. Se requiere rol de administrador.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        users = []
        # Listar usuarios de Firebase
        for user in auth.list_users().iterate_users():
            # Obtener custom claims
            custom_claims = user.custom_claims or {}
            role = custom_claims.get('role', 'sin_rol')
            
            users.append({
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name,
                'role': role,
                'email_verified': user.email_verified,
                'disabled': user.disabled,
                'creation_time': user.user_metadata.creation_timestamp.isoformat() if user.user_metadata.creation_timestamp else None
            })
        
        return Response({
            'users': users,
            'total': len(users)
        })
        
    except Exception as e:
        return Response({
            'error': f'Error listando usuarios: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
def update_user_role(request, uid):
    """
    Cambiar el rol de un usuario existente
    """
    if not hasattr(request, 'firebase_user_role') or request.firebase_user_role != 'admin':
        return Response({
            'error': 'Acceso denegado. Se requiere rol de administrador.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        new_role = request.data.get('role')
        
        if new_role not in ['admin', 'receptionist', 'housekeeping']:
            return Response({
                'error': 'Role debe ser "admin", "receptionist" o "housekeeping"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Actualizar custom claims
        auth.set_custom_user_claims(uid, {'role': new_role})
        
        return Response({
            'message': 'Rol actualizado exitosamente',
            'user_id': uid,
            'new_role': new_role
        })
        
    except auth.UserNotFoundError:
        return Response({
            'error': 'Usuario no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Error actualizando rol: {str(e)}'
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
        auth.delete_user(uid)
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