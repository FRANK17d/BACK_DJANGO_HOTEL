from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse

@api_view(['GET'])
def test_auth(request):
    """Endpoint de prueba para verificar autenticación"""
    if hasattr(request, 'firebase_user_id') and request.firebase_user_id:
        return Response({
            'message': 'Autenticación exitosa',
            'user_id': request.firebase_user_id,
            'role': request.firebase_user_role,
            'email': request.firebase_user_email
        })
    else:
        return Response({
            'error': 'No autenticado'
        }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
def admin_dashboard_data(request):
    """Endpoint específico para administradores"""
    if not hasattr(request, 'firebase_user_role') or request.firebase_user_role != 'admin':
        return Response({
            'error': 'Acceso denegado. Se requiere rol de administrador.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    return Response({
        'message': 'Datos del dashboard de administrador',
        'data': {
            'total_usuarios': 150,
            'reservas_pendientes': 25,
            'ingresos_mes': 45000
        }
    })