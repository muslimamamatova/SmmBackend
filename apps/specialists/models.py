"""Модель профиля специалиста — «витрина» исполнителя на площадке."""

from django.conf import settings
from django.db import models

from apps.common.choices import ProfileStatus, Specialization, WorkFormat
from apps.common.models import Skill


class SpecialistProfile(models.Model):
    """Профиль специалиста: что умеет, сколько стоит, как с ним работать.

    Один пользователь с ролью «Специалист» имеет один такой профиль
    (``OneToOneField``). Профиль создаётся не при регистрации, а на шаге
    «Заполнить профиль», поэтому в коде постоянно встречается проверка
    ``hasattr(user, 'specialist_profile')``.

    Поля ``rating``, ``reviews_count`` и ``orders_count`` — денормализованные
    счётчики: они пересчитываются при появлении отзыва или завершении сделки
    (см. apps/orders/services.py), чтобы списки специалистов можно было
    сортировать без тяжёлых агрегатов на каждый запрос.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='specialist_profile',
    )

    # --- Профессия и описание ----------------------------------------------
    specialization = models.CharField(max_length=30, choices=Specialization.choices)
    bio = models.TextField(blank=True)                              # «о себе»
    experience_years = models.PositiveSmallIntegerField(default=0)  # стаж в годах

    # --- География и условия работы ----------------------------------------
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    price_from = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # «от» в прайсе
    price_to = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)    # «до» в прайсе
    work_format = models.CharField(max_length=20, choices=WorkFormat.choices, default=WorkFormat.REMOTE)

    # --- Дополнительные данные ---------------------------------------------
    languages = models.JSONField(default=list, blank=True)     # список языков: ["ru", "en"]
    social_links = models.JSONField(default=dict, blank=True)  # {"instagram": "...", "telegram": "..."}
    skills = models.ManyToManyField(Skill, blank=True, related_name='specialists')

    # --- Статус и репутация -------------------------------------------------
    status = models.CharField(max_length=20, choices=ProfileStatus.choices, default=ProfileStatus.NEWBIE)
    verified = models.BooleanField(default=False)      # проверен модератором
    is_available = models.BooleanField(default=True)   # готов брать заказы
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)  # средняя оценка 0.00–5.00
    reviews_count = models.PositiveIntegerField(default=0)                   # сколько отзывов учтено
    orders_count = models.PositiveIntegerField(default=0)                    # завершённых сделок

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'профиль специалиста'
        verbose_name_plural = 'профили специалистов'
        ordering = ['-created_at']
        # Индексы под самые частые сортировки каталога специалистов.
        indexes = [
            models.Index(fields=['specialization']),
            models.Index(fields=['-rating']),
        ]

    def __str__(self):
        """Например: «Анна Иванова (Таргетолог)» — удобно в админке и логах."""
        return f'{self.user.name} ({self.get_specialization_display()})'

    @property
    def price_range_display(self):
        """Человекочитаемый прайс для карточки специалиста.

        Возвращает строку вида «от 500 до 2000», «от 500», «до 2000» или
        «По договорённости», если цены не указаны.
        """
        if self.price_from and self.price_to:
            return f'от {self.price_from:g} до {self.price_to:g}'
        if self.price_from:
            return f'от {self.price_from:g}'
        if self.price_to:
            return f'до {self.price_to:g}'
        return 'По договорённости'
