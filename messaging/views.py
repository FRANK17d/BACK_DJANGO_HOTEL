from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Max, Count, Case, When, F
from .models import Conversation, Message
from authentication.models import UserProfile

@api_view(['GET'])
def list_conversations(request):
    """
    Listar todas las conversaciones del usuario autenticado
    """
    if not hasattr(request, 'firebase_user'):
        return Response({
            'error': 'Usuario no autenticado'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        uid = request.firebase_user['uid']
        user = UserProfile.objects.get(firebase_uid=uid)
        
        # Obtener conversaciones donde el usuario es participante
        conversations = Conversation.objects.filter(
            Q(participant1=user) | Q(participant2=user)
        ).annotate(
            last_message_time=Max('messages__created_at'),
            unread_count=Count(
                Case(
                    When(
                        messages__is_read=False,
                        messages__sender__firebase_uid__ne=uid,
                        then=1
                    )
                )
            )
        ).order_by('-last_message_time')
        
        result = []
        for conv in conversations:
            # Determinar el otro participante
            other_user = conv.participant2 if conv.participant1.firebase_uid == uid else conv.participant1
            
            # Obtener último mensaje
            last_msg = conv.messages.last()
            
            result.append({
                'conversation_id': conv.id,
                'other_user': {
                    'uid': other_user.firebase_uid,
                    'name': other_user.display_name or other_user.email.split('@')[0],
                    'email': other_user.email,
                    'role': other_user.role,
                    'photo': other_user.profile_photo_url or ''
                },
                'last_message': {
                    'text': last_msg.text if last_msg else '',
                    'timestamp': last_msg.created_at.isoformat() if last_msg else conv.created_at.isoformat(),
                    'sender_uid': last_msg.sender.firebase_uid if last_msg else ''
                } if last_msg else None,
                'unread_count': conv.unread_count,
                'updated_at': conv.updated_at.isoformat()
            })
        
        return Response({
            'conversations': result
        })
        
    except UserProfile.DoesNotExist:
        return Response({
            'error': 'Usuario no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Error listando conversaciones: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_messages(request, other_user_uid):
    """
    Obtener todos los mensajes de una conversación con otro usuario
    """
    if not hasattr(request, 'firebase_user'):
        return Response({
            'error': 'Usuario no autenticado'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        uid = request.firebase_user['uid']
        
        # Obtener o crear conversación
        conversation = Conversation.get_or_create_conversation(uid, other_user_uid)
        
        # Obtener mensajes
        messages = conversation.messages.all()
        
        # Marcar mensajes como leídos
        messages.filter(sender__firebase_uid=other_user_uid, is_read=False).update(is_read=True)
        
        result = []
        for msg in messages:
            result.append({
                'id': msg.id,
                'sender_uid': msg.sender.firebase_uid,
                'text': msg.text,
                'message_type': msg.message_type,
                'attachment': msg.attachment,
                'attachment_name': msg.attachment_name,
                'attachment_size': msg.attachment_size,
                'is_read': msg.is_read,
                'timestamp': msg.created_at.isoformat()
            })
        
        return Response({
            'conversation_id': conversation.id,
            'messages': result
        })
        
    except UserProfile.DoesNotExist:
        return Response({
            'error': 'Usuario no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Error obteniendo mensajes: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def send_message(request, other_user_uid):
    """
    Enviar un mensaje a otro usuario (texto, imagen o archivo)
    """
    if not hasattr(request, 'firebase_user'):
        return Response({
            'error': 'Usuario no autenticado'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        uid = request.firebase_user['uid']
        text = request.data.get('text', '').strip()
        message_type = request.data.get('message_type', 'text')
        attachment = request.data.get('attachment', '')
        attachment_name = request.data.get('attachment_name', '')
        attachment_size = request.data.get('attachment_size', 0)
        
        # Validar que al menos haya texto o archivo adjunto
        if not text and not attachment:
            return Response({
                'error': 'El mensaje debe contener texto o un archivo adjunto'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar tamaño de archivo (máximo 10MB en base64)
        if attachment and attachment_size > 10 * 1024 * 1024:
            return Response({
                'error': 'El archivo es demasiado grande. Máximo 10MB'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener o crear conversación
        conversation = Conversation.get_or_create_conversation(uid, other_user_uid)
        
        # Obtener usuario remitente
        sender = UserProfile.objects.get(firebase_uid=uid)
        
        # Crear mensaje
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            text=text,
            message_type=message_type,
            attachment=attachment,
            attachment_name=attachment_name,
            attachment_size=attachment_size
        )
        
        # Actualizar timestamp de la conversación
        conversation.save()  # Esto actualiza el updated_at
        
        return Response({
            'message': {
                'id': message.id,
                'sender_uid': message.sender.firebase_uid,
                'text': message.text,
                'message_type': message.message_type,
                'attachment': message.attachment,
                'attachment_name': message.attachment_name,
                'attachment_size': message.attachment_size,
                'is_read': message.is_read,
                'timestamp': message.created_at.isoformat()
            }
        }, status=status.HTTP_201_CREATED)
        
    except UserProfile.DoesNotExist:
        return Response({
            'error': 'Usuario no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Error enviando mensaje: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def list_users_for_messaging(request):
    """
    Listar todos los usuarios disponibles para iniciar una conversación
    (excluyendo al usuario autenticado) con conteo de mensajes no leídos
    """
    if not hasattr(request, 'firebase_user'):
        return Response({
            'error': 'Usuario no autenticado'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        uid = request.firebase_user['uid']
        current_user = UserProfile.objects.get(firebase_uid=uid)
        
        # Obtener todos los usuarios excepto el actual
        users = UserProfile.objects.exclude(firebase_uid=uid)
        
        result = []
        for user in users:
            # Buscar conversación con este usuario
            conversation = Conversation.objects.filter(
                (Q(participant1=current_user) & Q(participant2=user)) |
                (Q(participant1=user) & Q(participant2=current_user))
            ).first()
            
            unread_count = 0
            last_message = None
            last_message_time = None
            
            if conversation:
                # Contar mensajes no leídos de este usuario
                unread_count = conversation.messages.filter(
                    sender=user,
                    is_read=False
                ).count()
                
                # Obtener último mensaje
                last_msg = conversation.messages.last()
                if last_msg:
                    last_message = last_msg.text
                    last_message_time = last_msg.created_at.isoformat()
            
            result.append({
                'uid': user.firebase_uid,
                'name': user.display_name or user.email.split('@')[0],
                'email': user.email,
                'role': user.role,
                'photo': user.profile_photo_url or '',
                'unread_count': unread_count,
                'last_message': last_message,
                'last_message_time': last_message_time
            })
        
        return Response({
            'users': result
        })
        
    except Exception as e:
        return Response({
            'error': f'Error listando usuarios: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

