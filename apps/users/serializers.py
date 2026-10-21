"""
Сериализаторы приложения users — превращают модель User в JSON и обратно.
Используются только в REST API (веб-формы живут в apps/site/forms.py).
"""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.users.models import User, UserRole


class UserSerializer(serializers.ModelSerializer):
    """Публичные данные пользователя: отдаются в /me и вложены в другие ответы.

    Поля ``status`` и ``created_at`` только для чтения — менять статус может
    лишь администратор через административное API.
    """

    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'name', 'avatar', 'role', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']


class LogoutSerializer(serializers.Serializer):
    """Тело запроса на выход: refresh-токен, который нужно отозвать.

    Класс нужен и для валидации, и для корректной схемы в Swagger.
    """

    refresh = serializers.CharField(help_text='Refresh-токен, полученный при входе')


class RegisterSerializer(serializers.ModelSerializer):
    """Регистрация через API: создаёт пользователя и сразу хеширует пароль.

    Роль «администратор» через регистрацию недоступна — её может выставить
    только существующий админ или команда createsuperuser.
    """

    # write_only — пароль никогда не возвращается в ответе;
    # validate_password прогоняет его через AUTH_PASSWORD_VALIDATORS.
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=[UserRole.SPECIALIST, UserRole.EMPLOYER])

    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'name', 'password', 'role']

    def create(self, validated_data):
        """Создаёт пользователя через менеджер, чтобы пароль сохранился хешем.

        Прямой ``User.objects.create()`` записал бы пароль как есть, поэтому
        используется ``create_user``.
        """
        return User.objects.create_user(**validated_data)
