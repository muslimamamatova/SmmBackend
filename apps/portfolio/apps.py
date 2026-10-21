"""Конфигурация приложения portfolio."""

from django.apps import AppConfig


class PortfolioConfig(AppConfig):
    """Кейсы специалистов и лента работ площадки."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.portfolio'
    verbose_name = 'Портфолио'
