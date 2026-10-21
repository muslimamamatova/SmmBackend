"""Сериализаторы административного API."""

from rest_framework import serializers

from apps.common.models import Complaint
from apps.users.models import User


class AdminUserSerializer(serializers.ModelSerializer):
    """Пользователь глазами администратора.

    Единственное, что админ меняет напрямую через этот сериализатор, — ничего:
    блокировка/разблокировка идёт через отдельные действия ``block``/``unblock``
    (apps/adminpanel/views.py), а не произвольным PATCH, чтобы не задеть роль
    или персональные данные пользователя по ошибке.
    """

    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'name', 'avatar', 'role', 'status', 'is_staff', 'created_at']
        read_only_fields = ['id', 'email', 'phone', 'name', 'avatar', 'role', 'is_staff', 'created_at']


class AdminComplaintSerializer(serializers.ModelSerializer):
    """Жалоба глазами администратора: видно, кто и когда её разобрал.

    Решение (статус/комментарий) выставляется действиями ``resolve``/``reject``,
    а не прямым PATCH — так в базе всегда остаётся автор решения и время.
    """

    reporter_name = serializers.CharField(source='reporter.name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.name', read_only=True)

    class Meta:
        model = Complaint
        fields = [
            'id', 'reporter', 'reporter_name', 'target_type', 'target_id', 'reason', 'comment',
            'status', 'moderator_comment', 'resolved_by', 'resolved_by_name', 'resolved_at', 'created_at',
        ]
        read_only_fields = [
            'id', 'reporter', 'target_type', 'target_id', 'reason', 'comment',
            'resolved_by', 'resolved_at', 'created_at',
        ]
