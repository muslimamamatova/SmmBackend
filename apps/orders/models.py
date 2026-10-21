"""
Модели сделок (заказов) и отзывов.

:class:`Order` — сделка между компанией и специалистом, проходит по
состояниям из ``OrderStatus`` (см. apps/common/choices.py). Допустимые
переходы между статусами заданы в apps/orders/services.py, а не здесь —
модель только хранит данные.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.choices import OrderStatus
from apps.companies.models import Company
from apps.jobs.models import Job
from apps.specialists.models import SpecialistProfile


class Order(models.Model):
    """Сделка: компания платит специалисту за выполнение работы.

    ``job`` может быть пустым (``null=True``) — сделку можно создать и без
    вакансии, например по прямой договорённости; при удалении вакансии
    (``SET_NULL``) сама сделка не пропадает.
    """

    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='orders')
    specialist = models.ForeignKey(SpecialistProfile, on_delete=models.CASCADE, related_name='orders')

    price = models.DecimalField(max_digits=10, decimal_places=2)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.NEW)

    # Проставляются сервисным слоем при переходах start/complete (см. services.py).
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'сделка'
        verbose_name_plural = 'сделки'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return f'Order #{self.pk} ({self.company} -> {self.specialist})'


class Review(models.Model):
    """Отзыв по завершённой сделке.

    ``OneToOneField`` на ``Order`` — на одну сделку действует только один
    отзыв (кто из сторон написал первым, тот и оставил единственный отзыв;
    см. проверку ``hasattr(order, 'review')`` в apps/orders/services.py).

    Оценка разбита на общую и три частных критерия, чтобы карточка
    специалиста могла показывать детальную статистику, а не только среднее.
    """

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews_written')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews_received')

    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    quality_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    timeliness_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    communication_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    compliance_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'отзыв'
        verbose_name_plural = 'отзывы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Review for order #{self.order_id}'
