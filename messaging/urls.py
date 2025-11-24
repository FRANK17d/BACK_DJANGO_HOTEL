from django.urls import path
from . import views

urlpatterns = [
    # Listar conversaciones del usuario
    path('conversations/', views.list_conversations, name='list_conversations'),
    
    # Listar usuarios disponibles para mensajear
    path('users/', views.list_users_for_messaging, name='list_users_for_messaging'),
    
    # Obtener mensajes de una conversación
    path('messages/<str:other_user_uid>/', views.get_messages, name='get_messages'),
    
    # Enviar mensaje
    path('send/<str:other_user_uid>/', views.send_message, name='send_message'),
]
