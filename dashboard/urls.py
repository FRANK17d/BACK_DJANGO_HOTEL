from django.urls import path
from . import views

urlpatterns = [
    path('metrics/', views.dashboard_metrics),
    path('monthly-revenue/', views.monthly_revenue_chart),
    path('payment-methods/', views.payment_methods_chart),
    path('occupancy-weekly/', views.occupancy_weekly_chart),
    path('today-checkins-checkouts/', views.today_checkins_checkouts),
    path('recent-reservations/', views.recent_reservations),
    path('statistics/', views.statistics_chart),
    path('sync-statuses/', views.sync_all_statuses),
]

