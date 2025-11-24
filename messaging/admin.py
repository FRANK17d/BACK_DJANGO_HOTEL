from django.contrib import admin
from .models import Conversation, Message

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'participant1', 'participant2', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('participant1__email', 'participant2__email', 'participant1__display_name', 'participant2__display_name')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'text_preview', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('text', 'sender__email', 'sender__display_name')
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Texto'

