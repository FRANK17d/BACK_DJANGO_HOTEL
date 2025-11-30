from django.urls import path
from . import views

urlpatterns = [
    path('system/status/', views.system_status),
    path('system/update/', views.update_system_status),
    path('briquettes/history/', views.briquette_history),
    path('briquettes/register/', views.register_briquette_change),
    path('issues/', views.maintenance_issues),
    path('issues/report/', views.report_issue),
    path('issues/delete/<int:issue_id>/', views.delete_issue),
    path('rooms/blocked/', views.blocked_rooms),
    path('rooms/block/', views.block_room),
    path('rooms/unblock/<int:room_id>/', views.unblock_room),
]

