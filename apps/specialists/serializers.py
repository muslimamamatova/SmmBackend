"""Сериализаторы профиля специалиста."""

from rest_framework import serializers

from apps.common.models import Skill
from apps.specialists.models import SpecialistProfile
from apps.users.serializers import UserSerializer


class SpecialistProfileSerializer(serializers.ModelSerializer):
    """Профиль специалиста для API.

    Особенности:

    * ``user`` отдаётся вложенным объектом (имя, аватар), но не принимается
      на запись — владелец определяется по токену;
    * ``skills`` передаются списком id навыков;
    * поля ``*_display`` дают готовые русские подписи, чтобы клиенту не нужно
      было хранить словарь переводов;
    * репутация (рейтинг, счётчики) и флаг проверки — только для чтения, их
      меняет сервер.
    """

    user = UserSerializer(read_only=True)
    skills = serializers.PrimaryKeyRelatedField(queryset=Skill.objects.all(), many=True, required=False)
    specialization_display = serializers.CharField(source='get_specialization_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SpecialistProfile
        fields = [
            'id', 'user', 'specialization', 'specialization_display', 'bio', 'experience_years',
            'country', 'city', 'price_from', 'price_to', 'work_format', 'languages', 'social_links',
            'skills', 'status', 'status_display', 'verified', 'is_available', 'rating', 'reviews_count',
            'orders_count', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'verified', 'rating', 'reviews_count', 'orders_count',
            'created_at', 'updated_at',
        ]

    def create(self, validated_data):
        """Создаёт профиль и привязывает его к текущему пользователю.

        Поле ``user`` не берётся из запроса, иначе можно было бы создать
        профиль от чужого имени.
        """
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
