"""
Сервисный слой сделок — единое место, где описаны допустимые переходы статуса
и правило обновления рейтинга специалиста.

Используется и REST API (``apps/orders/views.py``), и веб-интерфейсом
(``apps/site/views.py``), поэтому бизнес-правила проверяются одинаково в обоих
случаях и их нужно менять только здесь.
"""

from django.db.models import Avg, Count, F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.common.choices import OrderStatus

# Из какого статуса можно перейти в какой. Ключ — целевой статус, значение —
# множество статусов, из которых в него разрешён переход.
ALLOWED_TRANSITIONS = {
    OrderStatus.ACCEPTED: {OrderStatus.NEW, OrderStatus.DISCUSSION},
    OrderStatus.IN_PROGRESS: {OrderStatus.ACCEPTED},
    OrderStatus.REVIEW: {OrderStatus.IN_PROGRESS},
    OrderStatus.COMPLETED: {OrderStatus.REVIEW, OrderStatus.IN_PROGRESS},
    OrderStatus.CANCELLED: {OrderStatus.NEW, OrderStatus.DISCUSSION, OrderStatus.ACCEPTED, OrderStatus.IN_PROGRESS},
}


def transition_order(order, new_status, extra_fields=None):
    """Переводит сделку в новый статус, если переход разрешён.

    Аргументы:
        order: сделка, статус которой меняем;
        new_status: целевой статус (значение из :class:`OrderStatus`);
        extra_fields: словарь дополнительных полей для записи вместе со
            статусом, например ``{'started_at': timezone.now()}``.

    Исключения:
        ValidationError — если из текущего статуса сделки нельзя перейти
        в запрошенный (например, пытаются «завершить» ещё не принятую сделку).

    Побочный эффект:
        При переходе в COMPLETED счётчик ``orders_count`` специалиста
        увеличивается на единицу (используется для сортировки каталога
        «по опытности»).
    """
    allowed_from = ALLOWED_TRANSITIONS[new_status]
    if order.status not in allowed_from:
        raise ValidationError(f'Cannot move order from "{order.status}" to "{new_status}"')

    order.status = new_status
    update_fields = ['status', 'updated_at']
    for field, value in (extra_fields or {}).items():
        setattr(order, field, value)
        update_fields.append(field)
    order.save(update_fields=update_fields)

    if new_status == OrderStatus.COMPLETED:
        # F() — атомарный инкремент в самой базе, без промежуточного чтения в Python.
        specialist = order.specialist
        type(specialist).objects.filter(pk=specialist.pk).update(orders_count=F('orders_count') + 1)


def accept_order(order):
    """Специалист принимает сделку к работе."""
    transition_order(order, OrderStatus.ACCEPTED)


def start_order(order):
    """Специалист приступает к работе — фиксируется время начала."""
    transition_order(order, OrderStatus.IN_PROGRESS, {'started_at': timezone.now()})


def submit_order(order):
    """Специалист сдаёт работу на проверку заказчику."""
    transition_order(order, OrderStatus.REVIEW)


def complete_order(order):
    """Заказчик принимает работу — сделка считается завершённой."""
    transition_order(order, OrderStatus.COMPLETED, {'completed_at': timezone.now()})


def cancel_order(order):
    """Любая из сторон отменяет сделку (до её завершения)."""
    transition_order(order, OrderStatus.CANCELLED)


def refresh_specialist_rating(profile):
    """Пересчитывает средний рейтинг и число отзывов специалиста.

    Вызывается после сохранения нового отзыва, полученного специалистом.
    Среднее берётся по всем отзывам, где специалист — получатель
    (``recipient``), и округляется до двух знаков, как и хранится поле
    ``rating`` в базе.

    Аргументы:
        profile: объект :class:`apps.specialists.models.SpecialistProfile`,
            чьи счётчики нужно обновить.
    """
    from apps.orders.models import Review   # локальный импорт — избегаем цикла orders/specialists

    stats = Review.objects.filter(recipient=profile.user).aggregate(avg=Avg('rating'), count=Count('id'))
    profile.rating = round(stats['avg'] or 0, 2)
    profile.reviews_count = stats['count'] or 0
    profile.save(update_fields=['rating', 'reviews_count'])


def submit_review(order, serializer):
    """Проверяет, можно ли оставить отзыв по сделке, и сохраняет его.

    Аргументы:
        order: сделка, по которой пишут отзыв;
        serializer: валидный :class:`apps.orders.serializers.ReviewSerializer`
            с контекстом ``{'request': request, 'order': order}``.

    Исключения:
        ValidationError — сделка ещё не завершена, либо отзыв по ней уже есть.

    Возвращает:
        Сохранённый объект :class:`apps.orders.models.Review`. Если получатель
        отзыва — специалист, его рейтинг пересчитывается сразу же, поэтому
        карточка специалиста не отстаёт от только что оставленного отзыва.
    """
    if order.status != OrderStatus.COMPLETED:
        raise ValidationError('Order must be completed before it can be reviewed')
    if hasattr(order, 'review'):
        raise ValidationError('This order has already been reviewed')

    review = serializer.save()

    if review.recipient_id == order.specialist.user_id:
        refresh_specialist_rating(order.specialist)

    return review
