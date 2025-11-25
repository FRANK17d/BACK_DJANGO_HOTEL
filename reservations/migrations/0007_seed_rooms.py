from django.db import migrations


def seed_rooms(apps, schema_editor):
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