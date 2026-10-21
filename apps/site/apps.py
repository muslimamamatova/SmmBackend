"""Конфигурация приложения site (веб-интерфейс на Django-шаблонах)."""

from django.apps import AppConfig


class SiteConfig(AppConfig):
    """HTML-фронтенд площадки: страницы на Django-шаблонах с сессионной авторизацией.

    label='frontend' задан явно — иначе имя приложения совпало бы с частым
    системным словом «site» и таблицы миграций назывались бы неочевидно.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.site'
    label = 'frontend'
    verbose_name = 'Веб-интерфейс'
