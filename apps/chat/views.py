"""API чатов и сообщений."""

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.chat.models import Chat
from apps.chat.serializers import ChatSerializer, MessageSerializer
from apps.chat.services import mark_messages_read
from apps.users.models import User


class ChatViewSet(viewsets.ModelViewSet):
    """/chats — чаты текущего пользователя.

    В отличие от веб-интерфейса (там чат всегда 1-на-1), через API можно
    создать чат сразу с несколькими участниками — например, для будущих
    групповых обсуждений заказа.
    """

    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        """Только чаты, в которых участвует текущий пользователь."""
        if getattr(self, 'swagger_fake_view', False):
            return Chat.objects.none()
        return Chat.objects.prefetch_related('participants', 'messages').filter(participants=self.request.user)

    def create(self, request, *args, **kwargs):
        """POST /chats/ — создаёт чат или возвращает уже существующий по сделке.

        Текущий пользователь добавляется в список участников автоматически.
        Если указан ``order`` и чат по этой сделке уже существует, повторно
        создавать его не нужно — возвращается найденный.
        """
        participant_ids = set(request.data.get('participants', []))
        participant_ids.add(request.user.id)
        if len(participant_ids) < 2:
            raise ValidationError('A chat requires at least one other participant')

        participants = list(User.objects.filter(id__in=participant_ids))
        if len(participants) != len(participant_ids):
            raise ValidationError('One or more participants do not exist')

        order_id = request.data.get('order')
        if order_id:
            existing = self.get_queryset().filter(order_id=order_id).first()
            if existing:
                return Response(self.get_serializer(existing).data)

        chat = Chat.objects.create(order_id=order_id or None)
        chat.participants.set(participants)
        return Response(self.get_serializer(chat).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'])
    def messages(self, request, pk=None):
        """GET/POST /chats/{id}/messages/ — переписка конкретного чата.

        GET возвращает всю историю сообщений, POST отправляет новое
        сообщение от имени текущего пользователя.
        """
        chat = self.get_object()
        if request.method == 'GET':
            messages = chat.messages.select_related('sender')
            return Response(MessageSerializer(messages, many=True).data)

        serializer = MessageSerializer(data=request.data, context={'request': request, 'chat': chat})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk=None):
        """POST /chats/{id}/read/ — отмечает входящие сообщения чата прочитанными."""
        chat = self.get_object()
        mark_messages_read(chat, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
