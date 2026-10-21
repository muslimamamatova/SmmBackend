"""API компаний-заказчиков: список, карточка, своя компания."""

from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.companies.models import Company
from apps.companies.serializers import CompanySerializer
from apps.users.models import UserRole


class CompanyViewSet(viewsets.ModelViewSet):
    """/companies — публичный справочник компаний и управление своей компанией.

    Читать может любой (карточка компании видна на странице вакансии),
    создавать — авторизованный пользователь, менять и удалять — только
    владелец или администратор.
    """

    queryset = Company.objects.select_related('user').all()   # select_related убирает N+1
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    search_fields = ['name', 'industry', 'city', 'country']   # ?search=
    filterset_fields = ['industry', 'country', 'city']        # ?industry=...
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    def get_permissions(self):
        """Для создания компании достаточно быть авторизованным."""
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def perform_update(self, serializer):
        """Сохраняет изменения, если компания принадлежит автору запроса или он админ."""
        user = self.request.user
        if serializer.instance.user != user and user.role != UserRole.ADMIN:
            raise PermissionDenied('Not allowed to edit this company')
        serializer.save()

    def perform_destroy(self, instance):
        """Удаляет компанию; доступно владельцу и администратору."""
        user = self.request.user
        if instance.user != user and user.role != UserRole.ADMIN:
            raise PermissionDenied('Not allowed to delete this company')
        instance.delete()

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """GET /companies/me/ — компания текущего пользователя.

        Возвращает ``null``, если профиль компании ещё не создан: клиенту так
        проще показать экран «заполните профиль», чем разбирать 404.
        """
        company = Company.objects.filter(user=request.user).first()
        if not company:
            return Response(None)
        return Response(self.get_serializer(company).data)
