"""
ASGI-точка входа проекта (асинхронный аналог WSGI).

Нужна серверам вроде uvicorn/daphne, а также если в будущем добавить
WebSocket-чат вместо текущего опроса сообщений по таймеру.

Пример запуска:
    uvicorn config.asgi:application --host 0.0.0.0 --port 8000
"""

import os

from django.core.asgi import get_asgi_application

# Модуль настроек проекта.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# ASGI-приложение, которое вызывает сервер на каждый запрос/соединение.
application = get_asgi_application()
