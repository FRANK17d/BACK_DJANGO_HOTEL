from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0009_merge_20251124_1353'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='room_type',
            field=models.CharField(max_length=20, blank=True, null=True),
        ),
    ]