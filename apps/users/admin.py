"""Настройка отображения пользователей и OTP-кодов в админке Django."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import EmailOTP, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админка пользователя, адаптированная под вход по email.

    Базовый ``UserAdmin`` рассчитан на поле username, поэтому переопределены
    наборы полей. Флага ``is_active`` в формах нет намеренно: блокировкой
    управляет поле ``status`` (см. ``User.save``), и две ручки для одного и
    того же приводили бы к путанице.
    """

    ordering = ['-created_at']
    list_display = ['id', 'email', 'name', 'phone', 'role', 'status', 'is_staff', 'created_at']
    list_filter = ['role', 'status', 'is_staff']
    search_fields = ['email', 'name', 'phone']

    # Поля на странице редактирования существующего пользователя.
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Личные данные', {'fields': ('name', 'phone', 'avatar')}),
        ('Роль и статус', {
            'fields': ('role', 'status'),
            'description': 'Статус «Заблокирован» полностью запрещает вход на сайт и в API.',
        }),
        ('Права доступа', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login',)}),
    )

    # Поля на странице создания пользователя (пароль вводится дважды).
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'role'),
        }),
    )


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    """Просмотр отправленных кодов подтверждения — удобно при отладке почты."""

    list_display = ['id', 'email', 'code', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used']
    search_fields = ['email']
    readonly_fields = ['email', 'code', 'created_at', 'expires_at']
