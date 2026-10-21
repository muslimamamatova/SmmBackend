"""Конфигурация приложения jobs."""

from django.apps import AppConfig


class JobsConfig(AppConfig):
    """Вакансии и отклики специалистов на них."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.jobs'
    verbose_name = 'Вакансии'
