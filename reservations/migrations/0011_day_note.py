from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('reservations', '0010_reservation_room_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='DayNote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True)),
                ('text', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'calendar_day_notes',
                'ordering': ['-date'],
            },
        ),
    ]