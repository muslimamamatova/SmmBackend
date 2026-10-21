"""Конфигурация приложения specialists."""

from django.apps import AppConfig


class SpecialistsConfig(AppConfig):
    """Профили специалистов — витрина исполнителей площадки."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.specialists'
    verbose_name = 'Специалисты'
