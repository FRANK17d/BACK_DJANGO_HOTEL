#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt          # Instala dependencias
python manage.py collectstatic --no-input  # Recopila archivos estáticos
# Las migraciones se ejecutarán manualmente después del despliegue
python manage.py migrate