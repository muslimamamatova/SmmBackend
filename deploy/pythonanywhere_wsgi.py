"""
WSGI-файл для PythonAnywhere.

Содержимое этого файла копируется во вкладке Web → «WSGI configuration file»
(/var/www/mslm0990_pythonanywhere_com_wsgi.py).
"""

import os
import sys

# Путь к корню проекта (папка, где лежит manage.py).
PROJECT_DIR = '/home/mslm0990/SmmBackend'

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# python-decouple ищет .env относительно текущей папки и settings.py —
# переходим в корень проекта, чтобы .env гарантированно нашёлся.
os.chdir(PROJECT_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
