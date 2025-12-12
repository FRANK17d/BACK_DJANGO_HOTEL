from django.urls import path
from . import views

urlpatterns = [
    # Listar y crear huéspedes
    path('', views.list_huespedes, name='list_huespedes'),
    path('crear/', views.create_huesped, name='create_huesped'),
    
    # Obtener, actualizar y eliminar huésped específico
    path('<int:pk>/', views.get_huesped, name='get_huesped'),
    path('<int:pk>/actualizar/', views.update_huesped, name='update_huesped'),
    path('<int:pk>/eliminar/', views.delete_huesped, name='delete_huesped'),
    
    # API LOOKUP
    path('lookup/', views.lookup_document, name='lookup_document'),
    
]