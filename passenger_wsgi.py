import os, sys

BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'Django_Hotel'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Django_Hotel.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()