from django.db import models
from authentication.models import UserProfile

class Conversation(models.Model):
    """
    Modelo para representar una conversación entre dos usuarios
    """
    participant1 = models.ForeignKey(
        UserProfile, 
        on_delete=models.CASCADE, 
        related_name='conversations_as_participant1'
    )
    participant2 = models.ForeignKey(
        UserProfile, 
        on_delete=models.CASCADE, 
        related_name='conversations_as_participant2'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversations'
        # Asegurar que no haya conversaciones duplicadas
        unique_together = ('participant1', 'participant2')
    
    def __str__(self):
        return f"Conversación entre {self.participant1.display_name} y {self.participant2.display_name}"
    
    @staticmethod
    def get_or_create_conversation(user1_uid, user2_uid):
        """
        Obtener o crear una conversación entre dos usuarios.
        Normaliza el orden para evitar duplicados.
        """
        from authentication.models import UserProfile
        
        user1 = UserProfile.objects.get(firebase_uid=user1_uid)
        user2 = UserProfile.objects.get(firebase_uid=user2_uid)
        
        # Normalizar orden (siempre el menor uid primero)
        if user1_uid > user2_uid:
            user1, user2 = user2, user1
        
        conversation, created = Conversation.objects.get_or_create(
            participant1=user1,
            participant2=user2
        )
        return conversation

class Message(models.Model):
    """
    Modelo para representar un mensaje individual
    """
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Texto'),
        ('image', 'Imagen'),
        ('file', 'Archivo'),
    ]
    
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        UserProfile, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
    )
    text = models.TextField(blank=True)  # Ahora puede estar vacío si solo hay archivo
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default='text')
    
    # Campo para almacenar archivo/imagen en base64 o URL
    attachment = models.TextField(blank=True, null=True)
    attachment_name = models.CharField(max_length=255, blank=True, null=True)  # Nombre original del archivo
    attachment_size = models.IntegerField(blank=True, null=True)  # Tamaño en bytes
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'messages'
        ordering = ['created_at']
    
    def __str__(self):
        if self.message_type == 'text':
            return f"Mensaje de {self.sender.display_name} - {self.text[:50]}"
        else:
            return f"{self.message_type.capitalize()} de {self.sender.display_name} - {self.attachment_name}"


