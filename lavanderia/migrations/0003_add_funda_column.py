from django.db import migrations


def add_funda_column_if_not_exists(apps, schema_editor):
    """Agregar columna funda solo si no existe (compatible con MySQL)"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'lavanderia_laundryorder' 
            AND COLUMN_NAME = 'funda'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                ALTER TABLE `lavanderia_laundryorder` 
                ADD COLUMN `funda` INT UNSIGNED NOT NULL DEFAULT 0
            """)


def remove_funda_column_if_exists(apps, schema_editor):
    """Remover columna funda si existe"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'lavanderia_laundryorder' 
            AND COLUMN_NAME = 'funda'
        """)
        if cursor.fetchone()[0] > 0:
            cursor.execute("ALTER TABLE `lavanderia_laundryorder` DROP COLUMN `funda`")


class Migration(migrations.Migration):

    dependencies = [
        ('lavanderia', '0002_add_columns_if_not_exists'),
    ]

    operations = [
        migrations.RunPython(add_funda_column_if_not_exists, remove_funda_column_if_exists),
    ]
