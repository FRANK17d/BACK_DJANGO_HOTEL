from django.contrib import admin
from .models import Payment, Receipt


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'guest_name', 'type', 'method', 'amount', 'status', 'created_at')
    list_filter = ('type', 'method', 'status', 'created_at')
    search_fields = ('transaction_id', 'guest_name', 'reservation_code')


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('numero', 'senores', 'importe', 'total', 'fecha', 'cancelado_fecha', 'payment')
    list_filter = ('fecha', 'cancelado_fecha')
    search_fields = ('numero', 'senores', 'dni')
