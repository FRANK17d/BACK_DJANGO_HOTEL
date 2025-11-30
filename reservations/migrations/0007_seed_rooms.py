from django.db import migrations, connection


def seed_rooms(apps, schema_editor):
    # Primero, asegurarse de que la columna 'type' existe
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'rooms'
            AND COLUMN_NAME = 'type'
        """)
        type_column_exists = cursor.fetchone()[0] > 0
        
        if not type_column_exists:
            # Agregar la columna type si no existe
            cursor.execute("""
                ALTER TABLE rooms 
                ADD COLUMN type VARCHAR(10) NULL
            """)
    
    Room = apps.get_model('reservations', 'Room')
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
    for floor, items in data.items():
        for code, typ in items:
            Room.objects.update_or_create(code=code, defaults={'floor': floor, 'type': typ, 'status': 'Disponible'})


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0006_create_room'),
    ]

    operations = [
        migrations.RunPython(seed_rooms, migrations.RunPython.noop),
    ]