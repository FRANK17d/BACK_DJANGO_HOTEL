from django.contrib import admin
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        'reservation_id', 'channel', 'guest_name', 'room_label',
        'check_in', 'check_out', 'total_amount', 'status', 'paid',
        'created_at'
    )
    list_filter = ('channel', 'status', 'paid', 'check_in', 'check_out')
    search_fields = ('reservation_id', 'guest_name', 'room_label')
