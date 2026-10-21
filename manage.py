#!/usr/bin/env python
"""
Утилита командной строки Django — главная точка входа для всех команд проекта.

Запускать нужно интерпретатором из виртуального окружения проекта:

    venv\\Scripts\\python.exe manage.py runserver      # запустить сайт и API
    venv\\Scripts\\python.exe manage.py migrate        # применить миграции
    venv\\Scripts\\python.exe manage.py test           # прогнать тесты
    venv\\Scripts\\python.exe manage.py createsuperuser  # создать админа
"""
import os
import sys


def main():
    """Передаёт аргументы командной строки обработчику команд Django.

    Сначала указывает, где лежат настройки проекта (config/settings.py),
    затем вызывает execute_from_command_line — он сам находит нужную команду
    (runserver, migrate, test и т. д.) и выполняет её.
    """
    # Модуль настроек по умолчанию; переменную окружения можно переопределить
    # извне, чтобы запуститься с другими настройками.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Самая частая причина — забыли активировать виртуальное окружение
        # или не установили зависимости из requirements.txt.
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
