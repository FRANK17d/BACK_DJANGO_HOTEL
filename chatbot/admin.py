from django.contrib import admin
from .models import ChatbotSession, ChatbotMessage


@admin.register(ChatbotSession)
class ChatbotSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user_email', 'created_at', 'updated_at']
    search_fields = ['session_id', 'user_email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ChatbotMessage)
class ChatbotMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'role', 'content_preview', 'timestamp']
    list_filter = ['role', 'timestamp']
    search_fields = ['content', 'session__session_id']
    readonly_fields = ['timestamp']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Contenido'
