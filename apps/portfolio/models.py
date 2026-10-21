"""
Модели портфолио специалиста.

Один «кейс» (:class:`Portfolio`) — это рассказ о выполненной работе: задача
клиента, что сделано, результат. К кейсу прикрепляются файлы
(:class:`PortfolioMedia`) и лайки пользователей (:class:`PortfolioLike`).
"""

from django.conf import settings
from django.db import models

from apps.common.choices import Specialization
from apps.specialists.models import SpecialistProfile


class Portfolio(models.Model):
    """Кейс в портфолио специалиста.

    Счётчики ``likes_count`` и ``views_count`` хранятся прямо в записи
    (денормализация) и обновляются через ``F()``-выражения — так сортировка
    «по популярности» работает без агрегации по таблице лайков, а параллельные
    запросы не теряют инкременты.
    """

    specialist = models.ForeignKey(SpecialistProfile, on_delete=models.CASCADE, related_name='portfolio_items')

    # --- Содержание кейса ---------------------------------------------------
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=Specialization.choices)   # к какой профессии относится
    description = models.TextField(blank=True)    # краткое описание
    client_task = models.TextField(blank=True)    # что просил клиент
    work_done = models.TextField(blank=True)      # что было сделано
    result = models.TextField(blank=True)         # какой результат получили

    # --- Оформление и ссылки ------------------------------------------------
    cover = models.ImageField(upload_to='portfolio_covers/', null=True, blank=True)  # обложка в ленте
    tools = models.JSONField(default=list, blank=True)   # инструменты: ["Figma", "CapCut"]
    links = models.JSONField(default=list, blank=True)   # ссылки на работу

    # --- Период работы ------------------------------------------------------
    period_from = models.DateField(null=True, blank=True)
    period_to = models.DateField(null=True, blank=True)

    # --- Счётчики популярности ---------------------------------------------
    likes_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'кейс портфолио'
        verbose_name_plural = 'портфолио'
        ordering = ['-created_at']
        # Индексы под фильтр по категории и сортировку ленты работ.
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['-likes_count']),
        ]

    def __str__(self):
        return self.title


class PortfolioMediaType(models.TextChoices):
    """Тип прикреплённого к кейсу файла: картинка или видео."""

    IMAGE = 'image', 'Изображение'
    VIDEO = 'video', 'Видео'


class PortfolioMedia(models.Model):
    """Файл, прикреплённый к кейсу (скриншот, превью, видео).

    Поле ``order`` задаёт порядок показа в галерее — его можно менять, не
    перезагружая файлы.
    """

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='media')
    type = models.CharField(max_length=10, choices=PortfolioMediaType.choices, default=PortfolioMediaType.IMAGE)
    file = models.FileField(upload_to='portfolio_media/')
    order = models.PositiveSmallIntegerField(default=0)   # позиция в галерее

    class Meta:
        verbose_name = 'файл портфолио'
        verbose_name_plural = 'файлы портфолио'
        ordering = ['order', 'id']   # сначала по заданному порядку, затем по времени добавления

    def __str__(self):
        return f'{self.portfolio.title} media #{self.pk}'


class PortfolioLike(models.Model):
    """Лайк пользователя на кейсе.

    ``unique_together`` гарантирует «один пользователь — один лайк»: повторный
    запрос снимает лайк, а не добавляет второй.
    """

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portfolio_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'лайк портфолио'
        verbose_name_plural = 'лайки портфолио'
        unique_together = ('portfolio', 'user')

    def __str__(self):
        return f'{self.user} ♥ {self.portfolio_id}'
