import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import firebase_admin
from firebase_admin import auth as firebase_auth

@database_sync_to_async
def verify_firebase_token(token):
    """Verifica el token de Firebase de forma asíncrona"""
    if not firebase_admin._apps:
        raise Exception("Firebase no está inicializado")
    return firebase_auth.verify_id_token(token)

class PresenceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Obtener el token del query string
        query_string = self.scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if not token:
            await self.close(code=4001)
            return
        
        # Verificar el token de Firebase
        try:
            decoded_token = await verify_firebase_token(token)
            self.user_uid = decoded_token.get('uid')
            self.user_email = decoded_token.get('email')
            
            # Agregar al grupo de presencia
            await self.channel_layer.group_add(
                'presence',
                self.channel_name
            )
            
            await self.accept()
            
            # Enviar confirmación de conexión
            await self.send(text_data=json.dumps({
                'type': 'connection_status',
                'status': 'connected',
            }))
            
            # Notificar que el usuario está online
            await self.channel_layer.group_send(
                'presence',
                {
                    'type': 'user_online',
                    'user_uid': self.user_uid,
                    'user_email': self.user_email,
                }
            )
        except Exception as e:
            print(f"Error verificando token: {e}")
            await self.close(code=4003)

    async def disconnect(self, close_code):
        # Remover del grupo de presencia
        if hasattr(self, 'user_uid'):
            await self.channel_layer.group_discard(
                'presence',
                self.channel_name
            )
            
            # Notificar que el usuario está offline
            await self.channel_layer.group_send(
                'presence',
                {
                    'type': 'user_offline',
                    'user_uid': self.user_uid,
                    'user_email': self.user_email,
                }
            )

    async def receive(self, text_data):
        # Recibir mensajes del cliente (puede usarse para ping/pong)
        try:
            data = json.loads(text_data)
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'status': 'connected'
                }))
        except json.JSONDecodeError:
            pass

    async def user_online(self, event):
        # Enviar notificación cuando un usuario se conecta
        await self.send(text_data=json.dumps({
            'type': 'user_online',
            'user_uid': event['user_uid'],
            'user_email': event['user_email'],
        }))

    async def user_offline(self, event):
        # Enviar notificación cuando un usuario se desconecta
        await self.send(text_data=json.dumps({
            'type': 'user_offline',
            'user_uid': event['user_uid'],
            'user_email': event['user_email'],
        }))

    async def connection_status(self, event):
        # Enviar estado de conexión
        await self.send(text_data=json.dumps({
            'type': 'connection_status',
            'status': event['status'],
        }))

    async def maintenance_notification(self, event):
        # Enviar notificación de mantenimiento
        await self.send(text_data=json.dumps({
            'type': 'maintenance_notification',
            'message': event.get('message', ''),
            'title': event.get('title', 'Recordatorio de Mantenimiento'),
            'maintenance_date': event.get('maintenance_date', ''),
            'maintenance_time': event.get('maintenance_time', ''),
        }))

    async def new_message(self, event):
        # Enviar notificación de nuevo mensaje solo al destinatario
        target_uid = event.get('target_uid')
        if hasattr(self, 'user_uid') and self.user_uid == target_uid:
            await self.send(text_data=json.dumps({
                'type': 'new_message',
                'message': event.get('message'),
                'sender_uid': event.get('sender_uid'),
            }))

    async def general_notification(self, event):
        # Enviar notificación general (incidencias, bloqueos, etc.)
        # Solo enviar si el usuario actual no es el que creó la notificación
        created_by_uid = event.get('created_by_uid')
        current_user_uid = getattr(self, 'user_uid', None)
        
        print(f"general_notification recibida - Usuario actual: {current_user_uid}, Creada por: {created_by_uid}")
        
        # Si hay un created_by_uid y coincide con el usuario actual, no enviar
        if created_by_uid and current_user_uid:
            # Comparar como strings para asegurar coincidencia
            if str(current_user_uid).strip() == str(created_by_uid).strip():
                print(f"❌ FILTRANDO notificación para usuario {current_user_uid} (creada por el mismo usuario)")
                return  # No enviar notificación al usuario que la creó
        
        print(f"✅ ENVIANDO notificación a usuario {current_user_uid} (creada por {created_by_uid})")
        await self.send(text_data=json.dumps({
            'type': 'general_notification',
            'title': event.get('title', 'Notificación'),
            'message': event.get('message', ''),
            'notification_type': event.get('notification_type', 'info'),
            'data': event.get('data', {}),
            'timestamp': event.get('timestamp', None),
            'created_by_uid': created_by_uid,  # Incluir para referencia en frontend
        }))

