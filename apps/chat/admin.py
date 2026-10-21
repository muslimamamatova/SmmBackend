"""Отображение чатов и сообщений в админке."""

from django.contrib import admin

from apps.chat.models import Chat, Message


class MessageInline(admin.TabularInline):
    """Сообщения чата редактируются прямо на странице чата (только просмотр)."""

    model = Message
    extra = 0
    readonly_fields = ['sender', 'text', 'created_at']


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    """Список чатов со вложенными сообщениями."""

    list_display = ['id', 'order', 'created_at']
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Отдельные сообщения — удобно искать конкретное при разборе жалоб."""

    list_display = ['id', 'chat', 'sender', 'created_at', 'read_at']
    search_fields = ['sender__email', 'text']
