"""Конфигурация приложения chat."""

from django.apps import AppConfig


class ChatConfig(AppConfig):
    """Чаты и сообщения между пользователями площадки."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.chat'
    verbose_name = 'Чат'
