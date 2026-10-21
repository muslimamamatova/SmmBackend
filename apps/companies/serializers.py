"""Сериализатор компании-заказчика."""

from rest_framework import serializers

from apps.companies.models import Company
from apps.users.serializers import UserSerializer


class CompanySerializer(serializers.ModelSerializer):
    """Компания для API.

    Владелец (``user``) отдаётся вложенным объектом только для чтения — при
    создании он берётся из токена, чтобы нельзя было записать компанию на
    чужой аккаунт.
    """

    user = UserSerializer(read_only=True)

    class Meta:
        model = Company
        fields = [
            'id', 'user', 'name', 'logo', 'description', 'website', 'industry',
            'country', 'city', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Создаёт компанию и привязывает её к текущему пользователю."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
