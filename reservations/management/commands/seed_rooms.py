"""
Comando de Django para insertar habitaciones en la base de datos
Ejecutar con: python manage.py seed_rooms
"""
from django.core.management.base import BaseCommand
from reservations.models import Room


class Command(BaseCommand):
    help = 'Inserta las habitaciones del hotel en la base de datos'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando inserción de habitaciones...'))
        
        # Datos de las habitaciones
        data = {
            1: [
                ('111', 'DE'), ('112', 'DF'), ('113', 'M')
            ],
            2: [
                ('210', 'M'), ('211', 'DF'), ('212', 'DF'), ('213', 'M'), ('214', 'DF'), ('215', 'M')
            ],
            3: [
                ('310', 'M'), ('311', 'DF'), ('312', 'DF'), ('313', 'M'), ('314', 'DF'), ('315', 'TF')
            ],
        }
        
        created_count = 0
        updated_count = 0
        
        for floor, items in data.items():
            for code, typ in items:
                room, created = Room.objects.update_or_create(
                    code=code,
                    defaults={
                        'floor': floor,
                        'type': typ,
                        'status': 'Disponible'
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ Habitación {code} creada (Piso {floor}, Tipo: {typ})'))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'→ Habitación {code} actualizada (Piso {floor}, Tipo: {typ})'))
        
        total_rooms = Room.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n✓ Proceso completado!'))
        self.stdout.write(self.style.SUCCESS(f'  - Habitaciones creadas: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'  - Habitaciones actualizadas: {updated_count}'))
        self.stdout.write(self.style.SUCCESS(f'  - Total de habitaciones en BD: {total_rooms}'))

