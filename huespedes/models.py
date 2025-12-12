from django.db import models


class Huesped(models.Model):
    """
    Modelo para registro de huéspedes del hotel
    """
    # === INFORMACIÓN DE VENTA ===
    CANAL_VENTA_CHOICES = [
        ('BOOKING', 'Booking'),
        ('WHATSAPP', 'WhatsApp'),
        ('RECEPCION', 'Recepción'),
    ]
    
    COMPROBANTE_CHOICES = [
        ('BOLETA', 'Boleta'),
        ('FACTURA', 'Factura'),
    ]
    
    canal_venta = models.CharField(max_length=20, choices=CANAL_VENTA_CHOICES, default='RECEPCION', verbose_name="Canal de Venta")
    tipo_comprobante = models.CharField(max_length=20, choices=COMPROBANTE_CHOICES, default='BOLETA', verbose_name="Tipo de Comprobante")
    
    # === INFORMACIÓN PERSONAL ===
    TIPO_DOCUMENTO_CHOICES = [
        ('DNI', 'DNI'),
        ('CE', 'CE'),
        ('PASAPORTE', 'Pasaporte'),
    ]
    
    nombres_apellidos = models.CharField(max_length=200, verbose_name='Nombres y Apellidos Completos')
    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOCUMENTO_CHOICES, default='DNI', verbose_name="Tipo de Documento")
    numero_documento = models.CharField(max_length=20, verbose_name="Número de Documento")
    numero_ruc = models.CharField(max_length=11, blank=True, null=True, verbose_name="Número de RUC")
    nombre_o_razon_social = models.CharField(max_length=300, blank=True, null=True, verbose_name="Nombre o Razón Social")
    estado = models.CharField(max_length=50, blank=True, null=True, verbose_name="Estado RUC")
    condicion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Condición RUC")
    direccion_completa = models.TextField(blank=True, null=True, verbose_name="Dirección Completa")
    fecha_nacimiento = models.DateField(verbose_name="Fecha de Nacimiento")
    nacionalidad = models.CharField(max_length=50, default='Peruana', verbose_name="Nacionalidad")
    procedencia = models.CharField(max_length=100, verbose_name="Procedencia")
    
    # === INFORMACIÓN DE HOSPEDAJE ===
    TIPO_HABITACION_CHOICES = [
        ('SIMPLE', 'Simple'),
        ('DOBLE', 'Doble'),
        ('MATRIMONIAL', 'Matrimonial'),
        ('TRIPLE', 'Triple'),
    ]
    
    NUMERO_HABITACION_CHOICES = [
        ('111', '111'),
        ('112', '112'),
        ('113', '113'),
        ('210', '210'),
        ('211', '211'),
        ('212', '212'),
        ('213', '213'),
        ('214', '214'),
        ('215', '215'),
        ('310', '310'),
        ('311', '311'),
        ('312', '312'),
        ('313', '313'),
        ('314', '314'),
        ('315', '315'),
    ]
    
    METODO_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('YAPE', 'Yape'),
        ('TARJETA', 'Tarjeta Débito/Crédito'),
    ]
    
    check_in = models.DateField(verbose_name="Check-in")
    check_out = models.DateField(verbose_name="Check-out")
    tipo_habitacion = models.CharField(max_length=20, choices=TIPO_HABITACION_CHOICES, verbose_name="Tipo de Habitación")
    numero_habitacion = models.CharField(max_length=3, choices=NUMERO_HABITACION_CHOICES, verbose_name="Número de Habitación")
    tarifa_noche = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tarifa por Noche (S/.)")
    adultos = models.PositiveIntegerField(default=1, verbose_name="Adultos")
    ninos = models.PositiveIntegerField(default=0, verbose_name="Niños")
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='EFECTIVO', verbose_name="Método de Pago")
    observacion = models.TextField(blank=True, null=True, verbose_name="Observación")
    
    # === CAMPOS DE CONTROL ===
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro en Sistema")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    
    class Meta:
        db_table = 'huespedes'
        verbose_name = 'Huésped'
        verbose_name_plural = 'Huéspedes'
        ordering = ['-fecha_registro']
        indexes = [
            models.Index(fields=['numero_documento']),
            models.Index(fields=['check_in']),
            models.Index(fields=['-fecha_registro']),
        ]
    
    def __str__(self):
        return f"{self.nombres_apellidos} - {self.check_in.strftime('%d/%m/%Y')}"
    
    @property
    def duracion_estadia(self):
        """Retorna la duración de la estadía en días"""
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            return max(1, delta.days)
        return 0
    
    @property
    def total_estadia(self):
        """Calcula el total de la estadía"""
        return self.tarifa_noche * self.duracion_estadia
    
    @property
    def total_huespedes(self):
        """Total de huéspedes (adultos + niños)"""
        return self.adultos + self.ninos