from django.db import migrations, models, connection


def create_room_table_if_not_exists(apps, schema_editor):
    """Crear tabla rooms solo si no existe, y agregar columna type si falta"""
    with connection.cursor() as cursor:
        # Verificar si la tabla ya existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'rooms'
        """)
        table_exists = cursor.fetchone()[0] > 0
        
        if not table_exists:
            # Crear la tabla si no existe
            cursor.execute("""
                CREATE TABLE rooms (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    code VARCHAR(10) NOT NULL UNIQUE,
                    floor INT NOT NULL,
                    type VARCHAR(10) NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'Disponible'
                )
            """)
            # Crear índice para ordering
            cursor.execute("""
                CREATE INDEX rooms_floor_code_idx ON rooms(floor, code)
            """)
        else:
            # Si la tabla existe, verificar si tiene la columna 'type'
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'rooms'
                AND COLUMN_NAME = 'type'
            """)
            type_column_exists = cursor.fetchone()[0] > 0
            
            if not type_column_exists:
                # Agregar la columna type si no existe
                cursor.execute("""
                    ALTER TABLE rooms 
                    ADD COLUMN type VARCHAR(10) NULL
                """)
            
            # Verificar si existe el índice, si no, crearlo
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.STATISTICS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'rooms'
                AND INDEX_NAME = 'rooms_floor_code_idx'
            """)
            index_exists = cursor.fetchone()[0] > 0
            
            if not index_exists:
                cursor.execute("""
                    CREATE INDEX rooms_floor_code_idx ON rooms(floor, code)
                """)


def remove_room_table(apps, schema_editor):
    """Eliminar tabla rooms si existe"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'rooms'
        """)
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            cursor.execute("DROP TABLE IF EXISTS rooms")


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0005_companion_document_fields'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    create_room_table_if_not_exists,
                    reverse_code=remove_room_table
                ),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='Room',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('code', models.CharField(max_length=10, unique=True)),
                        ('floor', models.IntegerField()),
                        ('type', models.CharField(max_length=10, blank=True, null=True)),
                        ('status', models.CharField(max_length=50, default='Disponible')),
                    ],
                    options={
                        'db_table': 'rooms',
                        'ordering': ['floor', 'code'],
                    },
                ),
            ],
        ),
    ]