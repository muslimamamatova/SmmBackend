"""
Модели чата: беседа (:class:`Chat`) и сообщения в ней (:class:`Message`).

Чат может быть привязан к конкретной сделке (``order``) — тогда это
переговоры по заказу, либо существовать сам по себе — обычная переписка
между пользователями, начатая со страницы специалиста.
"""

from django.conf import settings
from django.db import models

from apps.orders.models import Order


class Chat(models.Model):
    """Беседа между несколькими пользователями (обычно — двумя).

    ``order`` — необязательная привязка к сделке; ``OneToOneField``, потому
    что у одной сделки может быть не более одного чата.
    """

    order = models.OneToOneField(Order, on_delete=models.CASCADE, null=True, blank=True, related_name='chat')
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chats')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'чат'
        verbose_name_plural = 'чаты'
        ordering = ['-created_at']

    def __str__(self):
        return f'Chat #{self.pk}'


class Message(models.Model):
    """Отдельное сообщение в чате.

    ``read_at`` пустой, пока получатель не открыл чат; по нему считается
    бейдж «непрочитанные сообщения» в шапке сайта.
    """

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='messages_sent')
    text = models.TextField(blank=True)
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'сообщение'
        verbose_name_plural = 'сообщения'
        ordering = ['created_at']   # в чате сообщения читаются по времени, от старых к новым
        indexes = [models.Index(fields=['chat', 'read_at'])]

    def __str__(self):
        return f'Message #{self.pk} in chat #{self.chat_id}'
