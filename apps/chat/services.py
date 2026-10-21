"""
Сервисный слой чата — создание беседы и отметка сообщений прочитанными.

Используется и REST API (``apps/chat/views.py``), и веб-интерфейсом
(``apps/site/views.py``), чтобы правило «что считается диалогом двух
пользователей» не разошлось между ними.
"""

from django.db.models import Count
from django.utils import timezone

from apps.chat.models import Chat


def get_or_create_direct_chat(user_a, user_b):
    """Находит существующий чат ровно между этими двумя пользователями или создаёт новый.

    «Ровно между двумя» проверяется через ``participant_count=2`` — иначе
    could быть найден групповой чат, где оба состоят, но не наедине.

    Аргументы:
        user_a: инициатор чата (как правило — текущий пользователь);
        user_b: второй собеседник.

    Возвращает:
        Объект :class:`Chat` — существующий или только что созданный.
    """
    chat = (
        Chat.objects.filter(participants=user_a)
        .filter(participants=user_b)
        .annotate(participant_count=Count('participants'))
        .filter(participant_count=2)
        .first()
    )
    if chat:
        return chat

    chat = Chat.objects.create()
    chat.participants.set([user_a, user_b])
    return chat


def mark_messages_read(chat, reader):
    """Отмечает прочитанными все сообщения чата, которые не отправлял сам читатель.

    Аргументы:
        chat: чат, который сейчас открыл пользователь;
        reader: пользователь, который читает чат (его собственные сообщения
            не трогаем — отправитель не может «прочитать» своё сообщение).
    """
    chat.messages.filter(read_at__isnull=True).exclude(sender=reader).update(read_at=timezone.now())
