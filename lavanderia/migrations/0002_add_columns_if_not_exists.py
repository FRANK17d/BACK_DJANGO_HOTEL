from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lavanderia', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE `lavanderia_laundrystock` "
                "ADD COLUMN IF NOT EXISTS `lavanderia` INT NOT NULL DEFAULT 0;"
            ),
            reverse_sql=(
                "ALTER TABLE `lavanderia_laundrystock` "
                "DROP COLUMN IF EXISTS `lavanderia`;"
            ),
        ),
        migrations.RunSQL(
            sql=(
                "ALTER TABLE `lavanderia_laundrystock` "
                "ADD COLUMN IF NOT EXISTS `danado` INT NOT NULL DEFAULT 0;"
            ),
            reverse_sql=(
                "ALTER TABLE `lavanderia_laundrystock` "
                "DROP COLUMN IF EXISTS `danado`;"
            ),
        ),
    ]