from django.db import models

# Create your models here.

class UserProfile(models.Model):
    """
    Modelo para almacenar información adicional de usuarios de Firebase
    """
    firebase_uid = models.CharField(max_length=128, unique=True, primary_key=True)
    email = models.EmailField()
    display_name = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=50, default='receptionist')
    salary = models.CharField(max_length=100, blank=True, null=True, default='S/')
    entry_date = models.DateField(blank=True, null=True)
    attendance = models.CharField(max_length=50, blank=True, null=True)
    profile_photo_url = models.TextField(blank=True, null=True)  # Base64 o URL de la foto de perfil
    email_verified = models.BooleanField(default=False)  # Indica si el correo está verificado
    email_verification_token = models.CharField(max_length=255, blank=True, null=True)  # Token para verificar el correo
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.display_name or self.email} ({self.role})"
