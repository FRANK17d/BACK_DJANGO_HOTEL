from django.urls import path
from . import views

urlpatterns = [
    path('stock/', views.stock_list),
    path('stock/upsert/', views.stock_upsert),
    path('orders/', views.list_orders),
    path('send/', views.send_to_laundry),
    path('return/<str:order_code>/', views.return_order),
    path('damage/', views.damage_update),
]