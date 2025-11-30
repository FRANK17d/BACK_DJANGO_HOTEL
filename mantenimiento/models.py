from django.db import models
from django.utils import timezone


class WaterHeatingSystem(models.Model):
    """Modelo para el sistema de agua caliente (singleton)"""
    STATUS_CHOICES = [
        ("Operativo", "Operativo"),
        ("En Mantenimiento", "En Mantenimiento"),
        ("Fuera de Servicio", "Fuera de Servicio"),
    ]
    
    operational_status = models.CharField(
        max_length=32, 
        choices=STATUS_CHOICES, 
        default="Operativo",
        verbose_name="Estado Operativo"
    )
    briquettes_this_month = models.PositiveIntegerField(
        default=0,
        verbose_name="Briquetas Este Mes"
    )
    last_maintenance_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Fecha Último Cambio"
    )
    last_maintenance_time = models.TimeField(
        null=True, 
        blank=True,
        verbose_name="Hora Último Cambio"
    )
    next_maintenance_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Fecha Próximo Cambio"
    )
    next_maintenance_time = models.TimeField(
        null=True, 
        blank=True,
        verbose_name="Hora Próximo Cambio"
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Sistema de Agua Caliente"
        verbose_name_plural = "Sistema de Agua Caliente"
    
    def __str__(self):
        return f"Sistema - {self.operational_status}"
    
    @classmethod
    def get_instance(cls):
        """Obtiene o crea la instancia única del sistema"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class BriquetteChange(models.Model):
    """Historial de cambios de briquetas"""
    date = models.DateField(verbose_name="Fecha")
    time = models.TimeField(verbose_name="Hora")
    quantity = models.PositiveIntegerField(verbose_name="Cantidad")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-date", "-time"]
        verbose_name = "Cambio de Briquetas"
        verbose_name_plural = "Cambios de Briquetas"
    
    def __str__(self):
        return f"Cambio {self.date} - {self.quantity} unid."


class MaintenanceIssue(models.Model):
    """Incidencias de mantenimiento"""
    PRIORITY_CHOICES = [
        ("Baja", "Baja"),
        ("Media", "Media"),
        ("Alta", "Alta"),
    ]
    
    room = models.CharField(max_length=100, verbose_name="Habitación/Área")
    problem = models.TextField(verbose_name="Problema")
    priority = models.CharField(
        max_length=16, 
        choices=PRIORITY_CHOICES, 
        default="Media",
        verbose_name="Prioridad"
    )
    technician = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name="Técnico Asignado"
    )
    reported_date = models.DateField(
        auto_now_add=True,
        verbose_name="Fecha de Reporte"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-reported_date", "-created_at"]
        verbose_name = "Incidencia"
        verbose_name_plural = "Incidencias"
    
    def __str__(self):
        return f"{self.room} - {self.problem[:50]}"


class BlockedRoom(models.Model):
    """Habitaciones bloqueadas por mantenimiento"""
    room = models.CharField(max_length=100, verbose_name="Habitación")
    reason = models.TextField(verbose_name="Razón de Bloqueo")
    blocked_until = models.DateField(verbose_name="Bloqueada Hasta")
    blocked_by = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name="Bloqueada Por"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Habitación Bloqueada"
        verbose_name_plural = "Habitaciones Bloqueadas"
    
    def __str__(self):
        return f"{self.room} - Bloqueada hasta {self.blocked_until}"
