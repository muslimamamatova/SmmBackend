"""Модель компании-заказчика."""

from django.conf import settings
from django.db import models


class Company(models.Model):
    """Профиль компании, от имени которой публикуются вакансии и сделки.

    Один пользователь с ролью «Компания» владеет одной компанией
    (``OneToOneField``). Профиль заполняется после регистрации, поэтому в коде
    встречается проверка ``hasattr(user, 'company')`` — без заполненной
    компании нельзя опубликовать вакансию или открыть сделку.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='company')

    name = models.CharField(max_length=150)                                      # название компании
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)  # логотип
    description = models.TextField(blank=True)                                   # чем занимается
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)                      # отрасль
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'компания'
        verbose_name_plural = 'компании'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
