"""Сериализаторы портфолио: кейс, прикреплённый файл."""

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.portfolio.models import Portfolio, PortfolioMedia


class PortfolioMediaSerializer(serializers.ModelSerializer):
    """Файл (изображение/видео), прикреплённый к кейсу портфолио."""

    class Meta:
        model = PortfolioMedia
        fields = ['id', 'type', 'file', 'order']


class PortfolioSerializer(serializers.ModelSerializer):
    """Кейс портфолио для API.

    ``media`` — вложенные файлы кейса (только чтение, добавляются отдельным
    экшеном ``/portfolio/{id}/media/``); ``is_liked`` — лайкнул ли кейс
    текущий пользователь, нужен, чтобы клиент сразу отрисовал нужное
    состояние кнопки.
    """

    media = PortfolioMediaSerializer(many=True, read_only=True)
    specialist_name = serializers.CharField(source='specialist.user.name', read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = [
            'id', 'specialist', 'specialist_name', 'title', 'category', 'description', 'client_task',
            'work_done', 'result', 'cover', 'tools', 'links', 'period_from', 'period_to',
            'likes_count', 'views_count', 'is_liked', 'media', 'created_at', 'updated_at',
        ]
        # Счётчики и владелец выставляет сервер, а не клиент.
        read_only_fields = ['id', 'specialist', 'likes_count', 'views_count', 'created_at', 'updated_at']

    def get_is_liked(self, obj) -> bool:
        """True, если кейс лайкнул именно автор текущего запроса."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(user=request.user).exists()

    def create(self, validated_data):
        """Создаёт кейс от имени профиля специалиста текущего пользователя.

        Если у пользователя ещё нет профиля специалиста (``specialist_profile``),
        явно сообщаем об этом вместо непонятного AttributeError/500.
        """
        user = self.context['request'].user
        profile = getattr(user, 'specialist_profile', None)
        if profile is None:
            raise ValidationError('Для добавления кейсов нужно сначала заполнить профиль специалиста')
        validated_data['specialist'] = profile
        return super().create(validated_data)
