"""Сериализаторы чатов и сообщений."""

from rest_framework import serializers

from apps.chat.models import Chat, Message
from apps.users.serializers import UserSerializer


class MessageSerializer(serializers.ModelSerializer):
    """Сообщение в чате.

    ``chat`` и ``sender`` только для чтения — оба подставляются сервером из
    контекста запроса в :meth:`create`.
    """

    sender_name = serializers.CharField(source='sender.name', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'chat', 'sender', 'sender_name', 'text', 'attachment', 'read_at', 'created_at']
        read_only_fields = ['id', 'chat', 'sender', 'read_at', 'created_at']

    def create(self, validated_data):
        """Отправляет сообщение от имени текущего пользователя в чат из контекста."""
        validated_data['chat'] = self.context['chat']
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class ChatSerializer(serializers.ModelSerializer):
    """Беседа со сводкой: последнее сообщение и число непрочитанных.

    Этого достаточно, чтобы отрисовать список чатов без отдельного запроса
    по каждому — сами сообщения загружаются только внутри открытого чата
    (действие ``/chats/{id}/messages/``).
    """

    participants_detail = UserSerializer(source='participants', many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'order', 'participants', 'participants_detail', 'last_message', 'unread_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_last_message(self, obj) -> MessageSerializer:
        """Последнее по времени сообщение чата — для превью в списке."""
        message = obj.messages.order_by('-created_at').first()
        return MessageSerializer(message).data if message else None

    def get_unread_count(self, obj) -> int:
        """Сколько сообщений чата ещё не прочитано текущим пользователем."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        return obj.messages.filter(read_at__isnull=True).exclude(sender=request.user).count()
