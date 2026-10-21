"""Конфигурация приложения orders."""

from django.apps import AppConfig


class OrdersConfig(AppConfig):
    """Сделки между компаниями и специалистами и отзывы по ним."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.orders'
    verbose_name = 'Сделки'
