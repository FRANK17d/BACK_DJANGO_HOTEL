from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0005_companion_document_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10, unique=True)),
                ('floor', models.IntegerField()),
                ('type', models.CharField(max_length=10, blank=True, null=True)),
                ('status', models.CharField(max_length=50, default='Disponible')),
            ],
            options={
                'db_table': 'rooms',
                'ordering': ['floor', 'code'],
            },
        ),
    ]