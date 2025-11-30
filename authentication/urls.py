from django.urls import path
from . import views, user_management

urlpatterns = [
    path('test/', views.test_auth, name='test_auth'),
    path('admin/dashboard/', views.admin_dashboard_data, name='admin_dashboard'),
    
    # Gestión de usuarios
    path('admin/users/create/', user_management.create_user_with_role, name='create_user'),
    path('admin/users/', user_management.list_users, name='list_users'),
    path('admin/users/<str:uid>/role/', user_management.update_user_role, name='update_role'),
    path('admin/users/<str:uid>/toggle-status/', user_management.toggle_user_status, name='toggle_user_status'),
    path('admin/users/<str:uid>/', user_management.delete_user, name='delete_user'),
    
    # Perfil propio (GET/PATCH)
    path('profile/', user_management.update_own_profile, name='get_own_profile'),
    path('profile/update/', user_management.update_own_profile, name='update_own_profile'),
    
    # Verificación de correo electrónico
    path('verify-email/', user_management.verify_email, name='verify_email'),
]
