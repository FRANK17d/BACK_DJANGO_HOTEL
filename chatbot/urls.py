from django.urls import path
from . import views

urlpatterns = [
    path('message/', views.process_message, name='process_message'),
    path('history/', views.get_conversation_history, name='get_history'),
    path('end-session/', views.end_session, name='end_session'),
]

