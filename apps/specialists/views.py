"""API профилей специалистов: каталог, свой профиль, отзывы, верификация."""

from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.common.choices import ProfileStatus
from apps.common.permissions import IsAdmin
from apps.orders.models import Review
from apps.orders.serializers import ReviewSerializer
from apps.specialists.filters import SpecialistProfileFilter
from apps.specialists.models import SpecialistProfile
from apps.specialists.serializers import SpecialistProfileSerializer
from apps.users.models import UserRole


class SpecialistProfileViewSet(viewsets.ModelViewSet):
    """/specialists — каталог специалистов и управление своим профилем.

    Читать каталог может кто угодно (это публичная витрина), создавать —
    любой авторизованный, редактировать и удалять — только владелец профиля
    или администратор, подтверждать (verify) — только администратор.
    """

    # select_related/prefetch_related убирают проблему N+1: пользователь и
    # навыки подгружаются одним-двумя запросами на всю страницу каталога.
    queryset = SpecialistProfile.objects.select_related('user').prefetch_related('skills').all()
    serializer_class = SpecialistProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filterset_class = SpecialistProfileFilter                      # ?specialization=&price_min=...
    search_fields = ['user__name', 'bio', 'city', 'country']       # ?search=
    ordering_fields = ['rating', 'orders_count', 'reviews_count', 'price_from', 'created_at']
    ordering = ['-created_at']

    def get_permissions(self):
        """Подбирает права под конкретное действие.

        * create — требуется только авторизация;
        * verify/unverify — только администратор;
        * остальное — правило по умолчанию (чтение всем, запись авторизованным),
          а принадлежность объекта проверяется в perform_update/perform_destroy.
        """
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        if self.action in ('verify', 'unverify'):
            return [IsAdmin()]
        return super().get_permissions()

    def perform_update(self, serializer):
        """Сохраняет изменения, если профиль принадлежит автору запроса или он админ."""
        user = self.request.user
        if serializer.instance.user != user and user.role != UserRole.ADMIN:
            raise PermissionDenied('Not allowed to edit this profile')
        serializer.save()

    def perform_destroy(self, instance):
        """Удаляет профиль; доступно владельцу и администратору."""
        user = self.request.user
        if instance.user != user and user.role != UserRole.ADMIN:
            raise PermissionDenied('Not allowed to delete this profile')
        instance.delete()

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """GET /specialists/me/ — профиль текущего пользователя.

        Возвращает ``null``, если профиль ещё не заполнен: клиенту так проще
        понять, что нужно показать экран «заполните профиль», чем разбирать 404.
        """
        profile = SpecialistProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response(None)
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def reviews(self, request, pk=None):
        """GET /specialists/{id}/reviews/ — отзывы, полученные этим специалистом.

        Отзывы привязаны к пользователю (а не к профилю), поэтому выбираем их
        по ``recipient``.
        """
        profile = self.get_object()
        reviews = Review.objects.select_related('author', 'recipient').filter(recipient=profile.user)
        return Response(ReviewSerializer(reviews, many=True).data)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """POST /specialists/{id}/verify/ — отметить профиль проверенным (админ).

        Новичку одновременно повышается статус до «Проверенный специалист»;
        если у профиля уже более высокий статус (TOP/PRO), он не понижается.
        """
        profile = self.get_object()
        profile.verified = True
        if profile.status == ProfileStatus.NEWBIE:
            profile.status = ProfileStatus.VERIFIED
        profile.save(update_fields=['verified', 'status'])
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=['post'])
    def unverify(self, request, pk=None):
        """POST /specialists/{id}/unverify/ — снять отметку о проверке (админ).

        Обратная операция к :meth:`verify`: статус «Проверенный» возвращается
        к «Новичку», более высокие статусы остаются как есть.
        """
        profile = self.get_object()
        profile.verified = False
        if profile.status == ProfileStatus.VERIFIED:
            profile.status = ProfileStatus.NEWBIE
        profile.save(update_fields=['verified', 'status'])
        return Response(self.get_serializer(profile).data)
