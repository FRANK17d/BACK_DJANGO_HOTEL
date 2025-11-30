from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='LaundryStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(max_length=32, unique=True, choices=[
                    ("TOALLAS_GRANDE", "Toalla grande"),
                    ("TOALLAS_MEDIANA", "Toalla mediana"),
                    ("TOALLAS_CHICA", "Toalla chica"),
                    ("SABANAS_MEDIA", "Sábana 1/2 plaza"),
                    ("SABANAS_UNA", "Sábana 1 plaza"),
                    ("CUBRECAMAS_MEDIA", "Cubrecama 1/2 plaza"),
                    ("CUBRECAMAS_UNA", "Cubrecama 1 plaza"),
                    ("FUNDAS", "Funda de almohada"),
                ])),
                ('disponible', models.PositiveIntegerField(default=0)),
                ('lavanderia', models.PositiveIntegerField(default=0)),
                ('danado', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Stock de lavandería',
                'verbose_name_plural': 'Stock de lavandería',
            },
        ),
        migrations.CreateModel(
            name='LaundryOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_code', models.CharField(max_length=32, unique=True)),
                ('toalla_grande', models.PositiveIntegerField(default=0)),
                ('toalla_mediana', models.PositiveIntegerField(default=0)),
                ('toalla_chica', models.PositiveIntegerField(default=0)),
                ('sabana_media_plaza', models.PositiveIntegerField(default=0)),
                ('sabana_una_plaza', models.PositiveIntegerField(default=0)),
                ('cubrecama_media_plaza', models.PositiveIntegerField(default=0)),
                ('cubrecama_una_plaza', models.PositiveIntegerField(default=0)),
                ('funda', models.PositiveIntegerField(default=0)),
                ('status', models.CharField(max_length=16, default='Enviado', choices=[('Enviado', 'Enviado'), ('Retornado', 'Retornado')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('returned_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
