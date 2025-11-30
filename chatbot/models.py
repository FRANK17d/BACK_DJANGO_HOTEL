from django.db import models
from django.utils import timezone


class ChatbotSession(models.Model):
    session_id = models.CharField(max_length=100, unique=True)
    user_email = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        db_table = 'chatbot_sessions'
    
    def __str__(self):
        return f"Session {self.session_id} - {self.user_email}"


class ChatbotMessage(models.Model):
    session = models.ForeignKey(ChatbotSession, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=[('user', 'Usuario'), ('assistant', 'Asistente')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
        db_table = 'chatbot_messages'
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
