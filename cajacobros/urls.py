from django.urls import path
from . import views

urlpatterns = [
    path('transactions/today/', views.list_today_transactions, name='list_today_transactions'),
    path('payments/create/', views.create_payment, name='create_payment'),
    path('totals/today/', views.today_totals, name='today_totals'),
    path('clients/today/', views.today_clients, name='today_clients'),
    path('clients/', views.all_clients, name='all_clients'),
    path('receipt/emit/', views.emit_receipt, name='emit_receipt'),
]