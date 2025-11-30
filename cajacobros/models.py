from django.db import models


class Payment(models.Model):
    transaction_id = models.CharField(max_length=20, unique=True)
    type = models.CharField(max_length=50)
    guest_name = models.CharField(max_length=200)
    method = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='Completado')
    reservation_code = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']


class Receipt(models.Model):
    payment = models.ForeignKey(Payment, related_name='receipts', on_delete=models.CASCADE)
    numero = models.CharField(max_length=20)
    fecha = models.DateField()
    senores = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300, blank=True, null=True)
    dni = models.CharField(max_length=20, blank=True, null=True)
    concepto = models.TextField(blank=True, null=True)
    importe = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    son = models.CharField(max_length=300, blank=True, null=True)
    cancelado_fecha = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'receipts'
        ordering = ['-created_at']
