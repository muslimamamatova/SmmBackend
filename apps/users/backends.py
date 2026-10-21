"""
Бэкенд авторизации проекта.

Подключается в settings.AUTHENTICATION_BACKENDS и используется функцией
``django.contrib.auth.authenticate()`` — то есть и формой входа на сайте,
и админкой Django.
"""

from django.contrib.auth.backends import ModelBackend

from apps.users.models import UserStatus


class ActiveStatusModelBackend(ModelBackend):
    """Обычная проверка «email + пароль», плюс запрет входа заблокированным.

    Стандартный ``ModelBackend`` смотрит только на поле ``is_active``. Мы
    дополнительно проверяем ``status``: так блокировка работает даже если
    ``is_active`` по какой-то причине разошёлся со статусом (например, запись
    обновили напрямую через ``queryset.update()``, минуя ``User.save()``).
    """

    #: Путь к бэкенду — нужен при явном вызове ``login(request, user, backend=...)``,
    #: например сразу после регистрации, когда пароль ещё не проверяли.
    PATH = 'apps.users.backends.ActiveStatusModelBackend'

    def user_can_authenticate(self, user):
        """Решает, пускать ли пользователя внутрь.

        Аргументы:
            user: найденный по email пользователь (или None).

        Возвращает:
            True — если аккаунт активен по флагу ``is_active`` И не заблокирован
            модератором; иначе False, и вход завершается ошибкой «неверный
            email или пароль».
        """
        if not super().user_can_authenticate(user):
            return False
        return getattr(user, 'status', UserStatus.ACTIVE) != UserStatus.BLOCKED
