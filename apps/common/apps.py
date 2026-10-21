"""Конфигурация приложения common."""

from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Общие справочники и сквозные сущности: навыки, избранное, уведомления, жалобы."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.common'
    verbose_name = 'Общее'
