from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0002_room'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='document_type',
            field=models.CharField(max_length=10, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='document_number',
            field=models.CharField(max_length=20, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='arrival_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='num_people',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='reservation',
            name='num_adults',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='reservation',
            name='num_children',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='reservation',
            name='num_rooms',
            field=models.IntegerField(default=1),
        ),
        migrations.CreateModel(
            name='Companion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('document_type', models.CharField(max_length=10, blank=True, null=True)),
                ('document_number', models.CharField(max_length=20, blank=True, null=True)),
                ('reservation', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='companions', to='reservations.reservation')),
            ],
            options={
                'db_table': 'companions',
                'ordering': ['id'],
            },
        ),
    ]