"""
WSGI-точка входа проекта.

Этот файл нужен продакшен-серверам (gunicorn, uWSGI, mod_wsgi): они ищут в нём
переменную ``application`` и через неё передают HTTP-запросы в Django.

Пример запуска:
    gunicorn config.wsgi:application --bind 0.0.0.0:8000
"""

import os

from django.core.wsgi import get_wsgi_application

# Указываем Django, какой модуль настроек использовать (если переменная
# окружения уже задана, она имеет приоритет).
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Собственно WSGI-приложение, которое вызывает сервер на каждый запрос.
application = get_wsgi_application()
