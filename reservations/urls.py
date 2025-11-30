from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_reservations, name='list_reservations'),
    path('create/', views.create_reservation, name='create_reservation'),
    path('calendar/', views.calendar_events, name='calendar_events'),
    path('calendar/notes/', views.calendar_notes, name='calendar_notes'),
    path('calendar/notes/<str:date>/', views.calendar_note_detail, name='calendar_note_detail'),
    path('rooms/available/', views.available_rooms, name='available_rooms'),
    path('rooms/all/', views.all_rooms, name='all_rooms'),
    path('lookup/', views.lookup_document, name='lookup_document'),
    path('clients/paid/', views.paid_clients, name='paid_clients'),
    path('clients/paid/details/', views.paid_clients_details, name='paid_clients_details'),
    path('<str:reservation_id>/', views.reservation_detail, name='reservation_detail'),
]