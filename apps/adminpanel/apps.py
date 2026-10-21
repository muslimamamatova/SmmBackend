"""Конфигурация приложения adminpanel."""

from django.apps import AppConfig


class AdminpanelConfig(AppConfig):
    """Административное REST API: модерация и статистика площадки.

    label='adminpanel' задан явно, чтобы не совпасть с другим приложением и
    чтобы таблицы миграций назывались предсказуемо.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.adminpanel'
    label = 'adminpanel'
    verbose_name = 'Административная панель (API)'
