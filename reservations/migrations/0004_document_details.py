from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0003_reservation_extras'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='address',
            field=models.CharField(max_length=300, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='department',
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='province',
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='district',
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='birth_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='sex',
            field=models.CharField(max_length=20, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='taxpayer_type',
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='business_status',
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='business_condition',
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
    ]