from django.urls import path
from . import views, user_management

urlpatterns = [
    path('test/', views.test_auth, name='test_auth'),
    path('admin/dashboard/', views.admin_dashboard_data, name='admin_dashboard'),
    
    # Gestión de usuarios
    path('admin/users/create/', user_management.create_user_with_role, name='create_user'),
    path('admin/users/', user_management.list_users, name='list_users'),
    path('admin/users/<str:uid>/role/', user_management.update_user_role, name='update_role'),
    path('admin/users/<str:uid>/', user_management.delete_user, name='delete_user'),
]