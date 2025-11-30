from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0004_document_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='companion',
            name='address',
            field=models.CharField(max_length=300, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='companion',
            name='department',
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='companion',
            name='province',
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='companion',
            name='district',
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='companion',
            name='taxpayer_type',
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='companion',
            name='business_status',
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='companion',
            name='business_condition',
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
    ]