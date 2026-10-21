"""Конфигурация приложения companies."""

from django.apps import AppConfig


class CompaniesConfig(AppConfig):
    """Компании-заказчики: от их имени публикуются вакансии и открываются сделки."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.companies'
    verbose_name = 'Компании'
