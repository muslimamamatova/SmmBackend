"""API вакансий и откликов на них."""

from django.db import models
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.jobs.filters import JobFilter
from apps.jobs.models import Application, Job
from apps.jobs.serializers import ApplicationSerializer, JobSerializer
from apps.jobs.services import accept_application, reject_application, withdraw_application
from apps.users.models import UserRole


class JobViewSet(viewsets.ModelViewSet):
    """/jobs — каталог вакансий, публикация, модерация, отклики.

    Читать может любой; публиковать — любой авторизованный (сервер подставит
    его компанию); менять/удалять — владелец вакансии или администратор.
    """

    queryset = Job.objects.select_related('company').prefetch_related('skills').all()
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filterset_class = JobFilter                              # ?category=&budget_min=...
    search_fields = ['title', 'description']                 # ?search=
    ordering_fields = ['created_at', 'budget_from', 'budget_to', 'deadline']
    ordering = ['-created_at']

    def get_permissions(self):
        """Публикация вакансии требует только авторизации."""
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def perform_update(self, serializer):
        """Сохраняет изменения, если вакансия принадлежит автору запроса или он админ."""
        user = self.request.user
        if serializer.instance.company.user != user and user.role != UserRole.ADMIN:
            raise PermissionDenied('Not allowed to edit this job')
        serializer.save()

    def perform_destroy(self, instance):
        """Удаляет вакансию; доступно владельцу и администратору."""
        user = self.request.user
        if instance.company.user != user and user.role != UserRole.ADMIN:
            raise PermissionDenied('Not allowed to delete this job')
        instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def moderate(self, request, pk=None):
        """POST /jobs/{id}/moderate/ — закрыть или отменить вакансию (только админ).

        Тело запроса: ``{"status": "closed"}`` или ``{"status": "cancelled"}``.
        """
        if request.user.role != UserRole.ADMIN:
            raise PermissionDenied('Only an admin can moderate a job')

        job = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ('closed', 'cancelled'):
            raise ValidationError('status must be "closed" or "cancelled"')

        job.status = new_status
        job.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(job).data)

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.IsAuthenticated])
    def applications(self, request, pk=None):
        """GET/POST /jobs/{id}/applications/ — отклики на конкретную вакансию.

        GET — список откликов видит только компания-владелец вакансии;
        POST — отправить отклик (специалист отправляет его сам на себя,
        проверка роли происходит в сериализаторе через ``user.specialist_profile``).
        """
        job = self.get_object()

        if request.method == 'GET':
            if job.company.user != request.user:
                raise PermissionDenied('Not allowed to view applications for this job')
            applications = job.applications.select_related('specialist__user')
            serializer = ApplicationSerializer(applications, many=True, context=self.get_serializer_context())
            return Response(serializer.data)

        serializer = ApplicationSerializer(data=request.data, context={**self.get_serializer_context(), 'job': job})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    """/applications — отклики, видимые текущему пользователю, и действия с ними.

    В список попадают только отклики, где пользователь — либо откликнувшийся
    специалист, либо владелец вакансии (через компанию).
    """

    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Отклики, где текущий пользователь — одна из сторон."""
        if getattr(self, 'swagger_fake_view', False):
            return Application.objects.none()
        user = self.request.user
        return Application.objects.select_related('job__company', 'specialist__user').filter(
            models.Q(job__company__user=user) | models.Q(specialist__user=user)
        )

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """POST /applications/{id}/accept/ — компания принимает отклик.

        Принятие отклика открывает сделку (см. apps.jobs.services.accept_application)
        и переводит вакансию в статус «В работе».
        """
        application = self.get_object()
        if application.job.company.user != request.user:
            raise PermissionDenied('Only the job owner can accept this application')
        accept_application(application)
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """POST /applications/{id}/reject/ — компания отклоняет отклик."""
        application = self.get_object()
        if application.job.company.user != request.user:
            raise PermissionDenied('Only the job owner can reject this application')
        reject_application(application)
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """POST /applications/{id}/withdraw/ — специалист отзывает свой отклик."""
        application = self.get_object()
        if application.specialist.user != request.user:
            raise PermissionDenied('Only the applicant can withdraw this application')
        withdraw_application(application)
        return Response(self.get_serializer(application).data)
