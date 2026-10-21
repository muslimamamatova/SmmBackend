"""
Административное API: управление пользователями, разбор жалоб, сводная
статистика площадки. Доступно только пользователям с ролью «Администратор»
(проверяется разрешением :class:`apps.common.permissions.IsAdmin`).
"""

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.adminpanel.serializers import AdminComplaintSerializer, AdminUserSerializer
from apps.common.choices import ComplaintStatus, JobStatus, OrderStatus
from apps.common.models import Complaint
from apps.common.permissions import IsAdmin
from apps.companies.models import Company
from apps.jobs.models import Application, Job
from apps.orders.models import Order
from apps.specialists.models import SpecialistProfile
from apps.users.models import User, UserRole, UserStatus

# Статусы сделки, которые считаются «ещё идущими» для статистики на дашборде.
ACTIVE_ORDER_STATUSES = [
    OrderStatus.NEW, OrderStatus.DISCUSSION, OrderStatus.ACCEPTED,
    OrderStatus.IN_PROGRESS, OrderStatus.REVIEW,
]


class AdminUserViewSet(viewsets.ModelViewSet):
    """/admin/users — список пользователей и их блокировка/разблокировка.

    Создание и произвольное изменение полей отключены намеренно (см.
    ``http_method_names``) — единственное, что должен делать администратор
    с чужим аккаунтом, это блокировать или снимать блокировку.
    """

    queryset = User.objects.all().order_by('-created_at')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['role', 'status']
    search_fields = ['email', 'name', 'phone']
    http_method_names = ['get', 'patch', 'post', 'head', 'options']

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        """POST /admin/users/{id}/block/ — блокирует вход пользователю.

        Благодаря ``User.save()`` (см. apps/users/models.py) блокировка
        одинаково действует и на вход через сайт, и на вход через API.
        """
        user = self.get_object()
        user.status = UserStatus.BLOCKED
        user.save(update_fields=['status'])
        return Response(self.get_serializer(user).data)

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        """POST /admin/users/{id}/unblock/ — возвращает пользователю доступ."""
        user = self.get_object()
        user.status = UserStatus.ACTIVE
        user.save(update_fields=['status'])
        return Response(self.get_serializer(user).data)


class AdminComplaintViewSet(viewsets.ModelViewSet):
    """/admin/complaints — разбор жалоб пользователей.

    Создавать жалобы через административное API не нужно (это делают
    пользователи через /complaints/), поэтому доступны только чтение и
    действия-решения.
    """

    queryset = Complaint.objects.select_related('reporter', 'resolved_by').all()
    serializer_class = AdminComplaintSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['target_type', 'reason', 'status']
    http_method_names = ['get', 'post', 'head', 'options']

    def _resolve(self, request, pk, new_status):
        """Общая часть решения по жалобе: статус, комментарий, кто и когда решил."""
        complaint = self.get_object()
        complaint.status = new_status
        complaint.moderator_comment = request.data.get('moderator_comment', complaint.moderator_comment)
        complaint.resolved_by = request.user
        complaint.resolved_at = timezone.now()
        complaint.save(update_fields=['status', 'moderator_comment', 'resolved_by', 'resolved_at'])
        return Response(self.get_serializer(complaint).data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """POST /admin/complaints/{id}/resolve/ — жалоба признана обоснованной."""
        return self._resolve(request, pk, ComplaintStatus.RESOLVED)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """POST /admin/complaints/{id}/reject/ — жалоба отклонена."""
        return self._resolve(request, pk, ComplaintStatus.REJECTED)


class AdminDashboardView(APIView):
    """GET /admin/dashboard/ — сводная статистика площадки для главного экрана панели."""

    permission_classes = [IsAdmin]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        """Собирает числа по пользователям, сделкам, вакансиям и жалобам.

        Каждое число — отдельный простой запрос (count/aggregate); для
        текущего объёма данных площадки это быстрее и понятнее, чем одна
        сложная агрегация.
        """
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        orders_qs = Order.objects.all()
        # Оборот считаем только по завершённым сделкам — именно за них были реальные деньги.
        turnover = orders_qs.filter(status=OrderStatus.COMPLETED).aggregate(total=Sum('price'))['total'] or 0

        popular_categories = list(
            Job.objects.values('category')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        return Response({
            'users': {
                'total': User.objects.count(),
                'new_this_week': User.objects.filter(created_at__gte=week_ago).count(),
                'new_this_month': User.objects.filter(created_at__gte=month_ago).count(),
                'specialists': User.objects.filter(role=UserRole.SPECIALIST).count(),
                'employers': User.objects.filter(role=UserRole.EMPLOYER).count(),
                'blocked': User.objects.filter(status=UserStatus.BLOCKED).count(),
            },
            'specialists_count': SpecialistProfile.objects.count(),
            'companies_count': Company.objects.count(),
            'jobs': {
                'total': Job.objects.count(),
                'open': Job.objects.filter(status=JobStatus.OPEN).count(),
            },
            'orders': {
                'total': orders_qs.count(),
                'active': orders_qs.filter(status__in=ACTIVE_ORDER_STATUSES).count(),
                'completed': orders_qs.filter(status=OrderStatus.COMPLETED).count(),
            },
            'applications_count': Application.objects.count(),
            'turnover': turnover,
            'popular_categories': popular_categories,
            'pending_complaints': Complaint.objects.filter(status=ComplaintStatus.PENDING).count(),
        })
