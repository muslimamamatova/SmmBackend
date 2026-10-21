"""
Права доступа для REST API.

Классы подставляются во вьюсеты через ``permission_classes`` и отвечают на два
вопроса: пустить ли запрос вообще (``has_permission``) и разрешено ли действие
с конкретным объектом (``has_object_permission``).
"""

from rest_framework import permissions

from apps.users.models import UserRole


class IsSpecialist(permissions.BasePermission):
    """Доступ только авторизованному пользователю с ролью «Специалист»."""

    message = 'Доступно только специалистам.'

    def has_permission(self, request, view):
        """Проверяет, что запрос сделан специалистом (иначе 403)."""
        user = request.user
        return bool(user and user.is_authenticated and user.role == UserRole.SPECIALIST)


class IsEmployer(permissions.BasePermission):
    """Доступ только авторизованному пользователю с ролью «Компания» (заказчик)."""

    message = 'Доступно только заказчикам.'

    def has_permission(self, request, view):
        """Проверяет, что запрос сделан заказчиком (иначе 403)."""
        user = request.user
        return bool(user and user.is_authenticated and user.role == UserRole.EMPLOYER)


class IsAdmin(permissions.BasePermission):
    """Доступ только администратору площадки (роль ADMIN).

    Используется для административного API и модераторских действий
    (блокировка пользователей, разбор жалоб, модерация вакансий).
    """

    message = 'Доступно только администраторам.'

    def has_permission(self, request, view):
        """Проверяет, что запрос сделан администратором (иначе 403)."""
        user = request.user
        return bool(user and user.is_authenticated and user.role == UserRole.ADMIN)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Читать может любой, изменять — только владелец объекта.

    Владелец определяется атрибутом, путь к которому задан в ``owner_field``.
    Поддерживается вложенность через точку, например ``'specialist.user'`` для
    кейса портфолио, где владелец — пользователь профиля специалиста.
    """

    #: Путь к пользователю-владельцу относительно объекта.
    owner_field = 'user'

    def has_object_permission(self, request, view, obj):
        """Разрешает безопасные методы всем, остальные — только владельцу.

        Аргументы:
            obj: объект, к которому обращается запрос.

        Возвращает:
            True для GET/HEAD/OPTIONS; для изменяющих методов — True, только
            если найденный по ``owner_field`` пользователь совпал с автором запроса.
        """
        if request.method in permissions.SAFE_METHODS:
            return True

        # Спускаемся по цепочке атрибутов: obj -> obj.specialist -> ...user
        owner = obj
        for part in self.owner_field.split('.'):
            owner = getattr(owner, part, None)

        return owner == request.user
