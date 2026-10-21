"""API портфолио: лента кейсов, управление своими кейсами, лайки и файлы."""

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.portfolio.models import Portfolio
from apps.portfolio.serializers import PortfolioMediaSerializer, PortfolioSerializer
from apps.portfolio.services import register_view, toggle_like


class PortfolioViewSet(viewsets.ModelViewSet):
    """/portfolio — публичная лента кейсов и редактирование своих работ.

    Читать может любой; создавать кейс — только специалист с заполненным
    профилем; менять и удалять — только автор кейса.
    """

    queryset = Portfolio.objects.select_related('specialist__user').prefetch_related('media', 'likes').all()
    serializer_class = PortfolioSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filterset_fields = ['category', 'specialist']            # ?category=&specialist=
    search_fields = ['title', 'description']                 # ?search=
    ordering_fields = ['created_at', 'likes_count', 'views_count']
    ordering = ['-created_at']

    def get_permissions(self):
        """Создание кейса требует авторизации (роль проверяет сериализатор)."""
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        """GET /portfolio/{id}/ — карточка кейса; попутно считает просмотр.

        Просмотр увеличивается на каждый запрос карточки (без защиты от
        накрутки — для статистики площадки этого достаточно).
        """
        instance = self.get_object()
        register_view(instance)
        return Response(self.get_serializer(instance).data)

    def perform_update(self, serializer):
        """Разрешает правку только автору кейса."""
        if serializer.instance.specialist.user != self.request.user:
            raise PermissionDenied('Not allowed to edit this portfolio item')
        serializer.save()

    def perform_destroy(self, instance):
        """Разрешает удаление только автору кейса."""
        if instance.specialist.user != self.request.user:
            raise PermissionDenied('Not allowed to delete this portfolio item')
        instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        """POST /portfolio/{id}/like/ — поставить или снять лайк (переключатель).

        Возвращает:
            ``{"liked": true|false, "likes_count": N}`` — итоговое состояние,
            чтобы клиенту не нужно было перезапрашивать карточку.
        """
        portfolio = self.get_object()
        liked = toggle_like(portfolio, request.user)
        return Response({'liked': liked, 'likes_count': portfolio.likes_count})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def media(self, request, pk=None):
        """POST /portfolio/{id}/media/ — прикрепить файл к кейсу (только автор).

        Ожидает multipart-запрос с полем ``file``; тип (изображение/видео) и
        порядок показа можно передать явно.
        """
        portfolio = self.get_object()
        if portfolio.specialist.user != request.user:
            raise PermissionDenied('Not allowed to edit this portfolio item')

        serializer = PortfolioMediaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(portfolio=portfolio)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
