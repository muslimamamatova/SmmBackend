"""Отображение общих моделей в админке Django."""

from django.contrib import admin

from apps.common.models import Complaint, Favorite, Notification, Skill


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    """Справочник навыков: единственное место, где он пополняется."""

    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Избранное пользователей — нужно в основном для отладки."""

    list_display = ['id', 'user', 'object_type', 'object_id', 'created_at']
    list_filter = ['object_type']
    search_fields = ['user__email']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Уведомления: видно, что и кому отправила система."""

    list_display = ['id', 'user', 'type', 'title', 'is_read', 'created_at']
    list_filter = ['type', 'is_read']
    search_fields = ['user__email', 'title']


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    """Жалобы. Основной разбор удобнее вести в панели сайта (/panel/complaints/)."""

    list_display = ['id', 'reporter', 'target_type', 'target_id', 'reason', 'status', 'created_at']
    list_filter = ['target_type', 'reason', 'status']
    search_fields = ['reporter__email', 'comment']
    readonly_fields = ['reporter', 'target_type', 'target_id', 'reason', 'comment', 'created_at']
