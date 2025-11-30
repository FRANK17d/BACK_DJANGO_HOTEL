from django.db import migrations


def add_columns_if_not_exists(apps, schema_editor):
    """Agregar columnas solo si no existen (compatible con MySQL)"""
    with schema_editor.connection.cursor() as cursor:
        # Verificar y agregar columna 'lavanderia'
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'lavanderia_laundrystock' 
            AND COLUMN_NAME = 'lavanderia'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                ALTER TABLE `lavanderia_laundrystock` 
                ADD COLUMN `lavanderia` INT NOT NULL DEFAULT 0
            """)
        
        # Verificar y agregar columna 'danado'
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'lavanderia_laundrystock' 
            AND COLUMN_NAME = 'danado'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                ALTER TABLE `lavanderia_laundrystock` 
                ADD COLUMN `danado` INT NOT NULL DEFAULT 0
            """)


def remove_columns_if_exists(apps, schema_editor):
    """Remover columnas si existen"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'lavanderia_laundrystock' 
            AND COLUMN_NAME = 'lavanderia'
        """)
        if cursor.fetchone()[0] > 0:
            cursor.execute("ALTER TABLE `lavanderia_laundrystock` DROP COLUMN `lavanderia`")
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'lavanderia_laundrystock' 
            AND COLUMN_NAME = 'danado'
        """)
        if cursor.fetchone()[0] > 0:
            cursor.execute("ALTER TABLE `lavanderia_laundrystock` DROP COLUMN `danado`")


class Migration(migrations.Migration):

    dependencies = [
        ('lavanderia', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_columns_if_not_exists, remove_columns_if_exists),
    ]
