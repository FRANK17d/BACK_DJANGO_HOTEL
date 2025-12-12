from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Huesped
from .serializers import HuespedSerializer
import os
import json
from django.conf import settings
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


@api_view(['GET'])
def list_huespedes(request):
    """
    Lista todos los huéspedes registrados
    """
    try:
        huespedes = Huesped.objects.all()
        serializer = HuespedSerializer(huespedes, many=True)
        return Response({
            'success': True,
            'count': huespedes.count(),
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def create_huesped(request):
    """
    Registra un nuevo huésped
    """
    try:
        serializer = HuespedSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Huésped registrado exitosamente',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_huesped(request, pk):
    """
    Obtiene un huésped específico por ID
    """
    try:
        huesped = Huesped.objects.get(pk=pk)
        serializer = HuespedSerializer(huesped)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except Huesped.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Huésped no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT', 'PATCH'])
def update_huesped(request, pk):
    """
    Actualiza los datos de un huésped
    """
    try:
        huesped = Huesped.objects.get(pk=pk)
        serializer = HuespedSerializer(huesped, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Huésped actualizado exitosamente',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Huesped.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Huésped no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_huesped(request, pk):
    """
    Elimina un huésped
    """
    try:
        huesped = Huesped.objects.get(pk=pk)
        huesped.delete()
        return Response({
            'success': True,
            'message': 'Huésped eliminado exitosamente'
        }, status=status.HTTP_200_OK)
    except Huesped.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Huésped no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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