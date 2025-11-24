# Generated manually
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_userprofile_is_activated'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='is_activated',
        ),
    ]
