"""Сериализаторы общих сущностей: навыки, избранное, уведомления, жалобы."""

from rest_framework import serializers

from apps.common.models import Complaint, Favorite, Notification, Skill


class SkillSerializer(serializers.ModelSerializer):
    """Навык из справочника — только чтение, список навыков ведёт администратор."""

    class Meta:
        model = Skill
        fields = ['id', 'name']


class FavoriteSerializer(serializers.ModelSerializer):
    """Запись избранного. Владелец подставляется автоматически."""

    class Meta:
        model = Favorite
        fields = ['id', 'object_type', 'object_id', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        """Создаёт запись от имени текущего пользователя.

        Поле ``user`` не принимается из запроса намеренно — иначе можно было бы
        добавить объект в чужое избранное.
        """
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    """Уведомление. Клиент может менять только признак «прочитано»."""

    class Meta:
        model = Notification
        fields = ['id', 'type', 'title', 'text', 'link', 'is_read', 'created_at']
        # Содержимое уведомления формирует сервер, клиенту его менять нельзя.
        read_only_fields = ['id', 'type', 'title', 'text', 'link', 'created_at']


class ComplaintSerializer(serializers.ModelSerializer):
    """Жалоба в «пользовательском» виде: поля модерации доступны только для чтения."""

    reporter_name = serializers.CharField(source='reporter.name', read_only=True)

    class Meta:
        model = Complaint
        fields = [
            'id', 'reporter', 'reporter_name', 'target_type', 'target_id', 'reason', 'comment',
            'status', 'moderator_comment', 'resolved_at', 'created_at',
        ]
        # Статус и решение модератора выставляет административное API.
        read_only_fields = ['id', 'reporter', 'status', 'moderator_comment', 'resolved_at', 'created_at']

    def create(self, validated_data):
        """Создаёт жалобу от имени текущего пользователя (автора подставляет сервер)."""
        validated_data['reporter'] = self.context['request'].user
        return super().create(validated_data)
