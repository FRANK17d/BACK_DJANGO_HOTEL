"""
Management command para verificar y enviar notificaciones de mantenimiento
Ejecutar con: python manage.py check_maintenance
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from mantenimiento.models import WaterHeatingSystem
import time


class Command(BaseCommand):
    help = 'Verifica periódicamente si ha llegado la hora del próximo cambio de briquetas y envía notificaciones'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando verificador de mantenimiento...'))
        channel_layer = get_channel_layer()
        
        while True:
            try:
                system = WaterHeatingSystem.get_instance()
                
                if system.next_maintenance_date and system.next_maintenance_time:
                    # Obtener fecha y hora actual
                    now = timezone.localtime()
                    current_date = now.date()
                    current_time = now.time()
                    
                    # Combinar fecha y hora del próximo mantenimiento
                    maintenance_datetime = datetime.combine(
                        system.next_maintenance_date,
                        system.next_maintenance_time
                    )
                    current_datetime = datetime.combine(current_date, current_time)
                    
                    # Verificar si la hora ha llegado (con margen de 1 minuto)
                    time_diff = (maintenance_datetime - current_datetime).total_seconds()
                    
                    # Si está entre -60 y 60 segundos (1 minuto antes o después), enviar notificación
                    if -60 <= time_diff <= 60:
                        message = f"¡Es hora de realizar el cambio de briquetas! Fecha: {system.next_maintenance_date.strftime('%Y-%m-%d')} Hora: {system.next_maintenance_time.strftime('%I:%M %p')}"
                        
                        # Enviar a todos los usuarios conectados en el grupo 'presence'
                        async_to_sync(channel_layer.group_send)(
                            'presence',
                            {
                                'type': 'maintenance_notification',
                                'title': 'Recordatorio de Mantenimiento',
                                'message': message,
                                'maintenance_date': system.next_maintenance_date.strftime('%Y-%m-%d'),
                                'maintenance_time': system.next_maintenance_time.strftime('%I:%M %p'),
                            }
                        )
                        
                        self.stdout.write(self.style.SUCCESS(f'Notificación enviada: {message}'))
                
                # Verificar cada 30 segundos
                time.sleep(30)
                
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('\nDeteniendo verificador de mantenimiento...'))
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error: {e}'))
                time.sleep(30)

