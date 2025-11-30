from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lavanderia', '0002_add_columns_if_not_exists'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE `lavanderia_laundryorder` "
                "ADD COLUMN IF NOT EXISTS `funda` INT UNSIGNED NOT NULL DEFAULT 0;"
            ),
            reverse_sql=(
                "ALTER TABLE `lavanderia_laundryorder` "
                "DROP COLUMN IF EXISTS `funda`;"
            ),
        ),
    ]

