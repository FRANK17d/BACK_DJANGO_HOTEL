from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0007_seed_rooms'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReservationRoom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room_code', models.CharField(max_length=10)),
                ('reservation', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='assigned_rooms', to='reservations.reservation')),
            ],
            options={
                'db_table': 'reservation_rooms',
                'ordering': ['id'],
            },
        ),
    ]