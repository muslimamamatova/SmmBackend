"""API сделок и отзывов."""

from django.db import models
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.common.permissions import IsAdmin
from apps.orders.models import Order, Review
from apps.orders.serializers import OrderSerializer, ReviewSerializer
from apps.orders.services import accept_order, cancel_order, complete_order, start_order, submit_order, submit_review
from apps.users.models import UserRole


class OrderViewSet(viewsets.ModelViewSet):
    """/orders — сделки между компанией и специалистом.

    Список виден только участникам сделки (и администратору — ему видны
    все). Переходы между статусами делаются отдельными действиями, а не
    произвольным PATCH, чтобы нельзя было перескочить, например, сразу в
    «Завершён» из «Новый».
    """

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'job']
    ordering_fields = ['created_at', 'deadline', 'price']
    ordering = ['-created_at']

    def get_queryset(self):
        """Админ видит все сделки, остальные — только свои (как компания или специалист)."""
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        user = self.request.user
        base = Order.objects.select_related('company', 'specialist__user', 'job')
        if user.role == UserRole.ADMIN:
            return base.all()
        return base.filter(models.Q(company__user=user) | models.Q(specialist__user=user))

    def perform_create(self, serializer):
        """Создать сделку может только пользователь с заполненным профилем компании."""
        if not hasattr(self.request.user, 'company'):
            raise PermissionDenied('Only a company can create an order')
        serializer.save()

    def perform_update(self, serializer):
        """Сохраняет изменения, если сделка принадлежит автору запроса или он админ."""
        user = self.request.user
        if serializer.instance.company.user != user and user.role != UserRole.ADMIN:
            raise PermissionDenied('Not allowed to edit this order')
        serializer.save()

    def perform_destroy(self, instance):
        """Удаляет сделку; доступно владельцу-компании и администратору."""
        user = self.request.user
        if instance.company.user != user and user.role != UserRole.ADMIN:
            raise PermissionDenied('Not allowed to delete this order')
        instance.delete()

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """POST /orders/{id}/accept/ — специалист принимает сделку к работе."""
        order = self.get_object()
        if order.specialist.user != request.user:
            raise PermissionDenied('Only the specialist can accept this order')
        accept_order(order)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """POST /orders/{id}/start/ — специалист отмечает начало работы."""
        order = self.get_object()
        if order.specialist.user != request.user:
            raise PermissionDenied('Only the specialist can start this order')
        start_order(order)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """POST /orders/{id}/submit/ — специалист сдаёт работу на проверку."""
        order = self.get_object()
        if order.specialist.user != request.user:
            raise PermissionDenied('Only the specialist can submit this order for review')
        submit_order(order)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """POST /orders/{id}/complete/ — заказчик принимает выполненную работу."""
        order = self.get_object()
        if order.company.user != request.user:
            raise PermissionDenied('Only the company can complete this order')
        complete_order(order)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """POST /orders/{id}/cancel/ — любая из сторон (или админ) отменяет сделку."""
        order = self.get_object()
        user = request.user
        if user not in (order.company.user, order.specialist.user) and user.role != UserRole.ADMIN:
            raise PermissionDenied('Not allowed to cancel this order')
        cancel_order(order)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """POST /orders/{id}/review/ — оставить отзыв по завершённой сделке.

        Доступно только участникам сделки; правила «сделка завершена» и
        «отзыв ещё не оставлен» проверяет apps.orders.services.submit_review.
        """
        order = self.get_object()
        if request.user not in (order.company.user, order.specialist.user):
            raise PermissionDenied('Not allowed to review this order')

        serializer = ReviewSerializer(data=request.data, context={'request': request, 'order': order})
        serializer.is_valid(raise_exception=True)
        submit_review(order, serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """/reviews — публичный список отзывов; удалять их может только администратор."""

    queryset = Review.objects.select_related('author', 'recipient', 'order')
    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['recipient', 'author']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']

    def get_permissions(self):
        """Удаление отзыва (например, за нарушение правил) доступно только администратору."""
        if self.action == 'destroy':
            return [IsAdmin()]
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        """Удаляет отзыв; счётчики специалиста не пересчитываются автоматически —

        это редкое модераторское действие, при необходимости рейтинг поправит
        сам администратор через /specialists/{id}/ или новый отзыв её обновит.
        """
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
