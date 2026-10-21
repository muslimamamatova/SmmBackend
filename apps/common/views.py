"""
API общих разделов: справочник навыков, избранное, уведомления, жалобы.

Общий принцип приватных списков: queryset всегда фильтруется по
``request.user``, поэтому пользователь физически не может получить чужие
записи — даже обратившись по прямому id.
"""

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.models import Complaint, Favorite, Notification, Skill
from apps.common.serializers import ComplaintSerializer, FavoriteSerializer, NotificationSerializer, SkillSerializer


class SkillViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /skills — справочник навыков для автодополнения и фильтров.

    Только чтение и без авторизации: список нужен в том числе на публичных
    страницах поиска. Пополняется через админку.
    """

    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [permissions.AllowAny]
    search_fields = ['name']   # поддержка ?search=рилс


class FavoriteViewSet(viewsets.ModelViewSet):
    """/favorites — избранное текущего пользователя.

    Разрешены только просмотр, добавление и удаление: «частично изменить»
    запись избранного смысла не имеет.
    """

    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        """Возвращает только избранное автора запроса.

        Проверка ``swagger_fake_view`` нужна генератору схемы: при построении
        документации запроса (и пользователя) нет, поэтому отдаём пустой набор.
        """
        if getattr(self, 'swagger_fake_view', False):
            return Favorite.objects.none()
        return Favorite.objects.filter(user=self.request.user)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """/notifications — уведомления текущего пользователя.

    Создаёт их сервер при событиях, поэтому POST для создания нет; доступны
    чтение, отметка одного уведомления прочитанным (PATCH) и «прочитать все».
    """

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'post', 'head', 'options']

    def get_queryset(self):
        """Только уведомления автора запроса (о swagger_fake_view см. выше)."""
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        """PATCH /notifications/{id}/ — помечает уведомление прочитанным.

        Тело запроса не важно: единственное действие, которое клиент может
        сделать с уведомлением, — это прочитать его.
        """
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        """POST /notifications/read-all/ — помечает прочитанными все уведомления.

        Одним UPDATE-запросом, без загрузки объектов в память.
        """
        self.get_queryset().update(is_read=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ComplaintViewSet(viewsets.ModelViewSet):
    """/complaints — жалобы, отправленные текущим пользователем.

    Пользователь может создать жалобу и посмотреть свои; изменять и удалять
    их нельзя. Разбор жалоб — в административном API (apps/adminpanel).
    """

    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        """Только жалобы, автором которых является текущий пользователь."""
        if getattr(self, 'swagger_fake_view', False):
            return Complaint.objects.none()
        return Complaint.objects.filter(reporter=self.request.user)
