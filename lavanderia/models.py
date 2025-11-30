from django.db import models


class LaundryStock(models.Model):
    CATEGORY_CHOICES = [
        ("TOALLAS_GRANDE", "Toalla grande"),
        ("TOALLAS_MEDIANA", "Toalla mediana"),
        ("TOALLAS_CHICA", "Toalla chica"),
        ("SABANAS_MEDIA", "Sábana 1/2 plaza"),
        ("SABANAS_UNA", "Sábana 1 plaza"),
        ("CUBRECAMAS_MEDIA", "Cubrecama 1/2 plaza"),
        ("CUBRECAMAS_UNA", "Cubrecama 1 plaza"),
        ("FUNDAS", "Funda de almohada"),
    ]

    category = models.CharField(max_length=32, unique=True, choices=CATEGORY_CHOICES)
    total = models.PositiveIntegerField(default=0, help_text="Total de inventario del hotel")
    disponible = models.PositiveIntegerField(default=0)
    lavanderia = models.PositiveIntegerField(default=0)
    danado = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Stock de lavandería"
        verbose_name_plural = "Stock de lavandería"

    def __str__(self):
        return f"{self.category} (disp:{self.disponible} lav:{self.lavanderia} dañ:{self.danado})"


class LaundryOrder(models.Model):
    STATUS_CHOICES = [
        ("Enviado", "Enviado"),
        ("Retornado", "Retornado"),
    ]

    order_code = models.CharField(max_length=32, unique=True)
    toalla_grande = models.PositiveIntegerField(default=0)
    toalla_mediana = models.PositiveIntegerField(default=0)
    toalla_chica = models.PositiveIntegerField(default=0)
    sabana_media_plaza = models.PositiveIntegerField(default=0)
    sabana_una_plaza = models.PositiveIntegerField(default=0)
    cubrecama_media_plaza = models.PositiveIntegerField(default=0)
    cubrecama_una_plaza = models.PositiveIntegerField(default=0)
    funda = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="Enviado")
    created_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Orden {self.order_code} - {self.status}"



