from django.db import models


class Reservation(models.Model):
    reservation_id = models.CharField(max_length=20, unique=True, blank=True)
    channel = models.CharField(max_length=50)
    guest_name = models.CharField(max_length=200)
    room_label = models.CharField(max_length=100)
    check_in = models.DateField()
    check_out = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=50, default='Confirmada')
    paid = models.BooleanField(default=False)
    document_type = models.CharField(max_length=10, blank=True, null=True)
    document_number = models.CharField(max_length=20, blank=True, null=True)
    arrival_time = models.TimeField(blank=True, null=True)
    departure_time = models.TimeField(blank=True, null=True)
    num_people = models.IntegerField(default=1)
    num_adults = models.IntegerField(default=1)
    num_children = models.IntegerField(default=0)
    num_rooms = models.IntegerField(default=1)
    address = models.CharField(max_length=300, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    room_type = models.CharField(max_length=20, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    sex = models.CharField(max_length=20, blank=True, null=True)
    taxpayer_type = models.CharField(max_length=100, blank=True, null=True)
    business_status = models.CharField(max_length=50, blank=True, null=True)
    business_condition = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        creating = not self.pk
        super().save(*args, **kwargs)
        if creating and not self.reservation_id:
            self.reservation_id = f"RES-{self.pk:03d}"
            super().save(update_fields=['reservation_id'])

    class Meta:
        db_table = 'reservations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reservation_id} - {self.guest_name}"


class Companion(models.Model):
    reservation = models.ForeignKey(Reservation, related_name='companions', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    document_type = models.CharField(max_length=10, blank=True, null=True)
    document_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=300, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    taxpayer_type = models.CharField(max_length=100, blank=True, null=True)
    business_status = models.CharField(max_length=50, blank=True, null=True)
    business_condition = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'companions'
        ordering = ['id']

    def __str__(self):
        return self.name


class Room(models.Model):
    code = models.CharField(max_length=10, unique=True)
    floor = models.IntegerField()
    type = models.CharField(max_length=10, blank=True, null=True)
    status = models.CharField(max_length=50, default='Disponible')

    class Meta:
        db_table = 'rooms'
        ordering = ['floor', 'code']

    def __str__(self):
        return f"{self.code}"


class ReservationRoom(models.Model):
    reservation = models.ForeignKey(Reservation, related_name='assigned_rooms', on_delete=models.CASCADE)
    room_code = models.CharField(max_length=10)

    class Meta:
        db_table = 'reservation_rooms'
        ordering = ['id']

    def __str__(self):
        return self.room_code


class DayNote(models.Model):
    date = models.DateField(unique=True)
    text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'calendar_day_notes'
        ordering = ['-date']

    def __str__(self):
        return f"{self.date}"
