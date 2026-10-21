"""
Модели вакансий и откликов.

:class:`Job` — вакансия, опубликованная компанией. :class:`Application` —
отклик специалиста на неё; при принятии отклика (см. apps/jobs/services.py)
по нему создаётся сделка (``apps.orders.Order``).
"""

from django.db import models

from apps.common.choices import ApplicationStatus, BudgetType, JobStatus, Specialization, WorkFormat
from apps.common.models import Skill
from apps.companies.models import Company
from apps.specialists.models import SpecialistProfile


class Job(models.Model):
    """Вакансия: что нужно сделать, за какой бюджет и в какой срок."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')

    # --- Содержание вакансии -------------------------------------------------
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=Specialization.choices)   # нужная специализация
    tasks = models.JSONField(default=list, blank=True)   # список конкретных задач

    # --- Бюджет и сроки -------------------------------------------------------
    budget_type = models.CharField(max_length=20, choices=BudgetType.choices, default=BudgetType.NEGOTIABLE)
    budget_from = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_to = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)

    # --- Формат и география ---------------------------------------------------
    work_format = models.CharField(max_length=20, choices=WorkFormat.choices, default=WorkFormat.REMOTE)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    skills = models.ManyToManyField(Skill, blank=True, related_name='jobs')   # нужные навыки
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.OPEN)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'вакансия'
        verbose_name_plural = 'вакансии'
        ordering = ['-created_at']
        indexes = [
            # Главный запрос каталога: открытые вакансии нужной категории.
            models.Index(fields=['status', 'category']),
        ]

    def __str__(self):
        return self.title


class Application(models.Model):
    """Отклик специалиста на вакансию: предложенная цена, срок, сообщение.

    ``unique_together`` не даёт специалисту откликнуться на одну вакансию
    дважды — повторная попытка должна встретить уже существующую запись.
    """

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    specialist = models.ForeignKey(SpecialistProfile, on_delete=models.CASCADE, related_name='applications')
    message = models.TextField(blank=True)                                                 # сопроводительное письмо
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)    # предложенная цена
    deadline = models.DateField(null=True, blank=True)                                     # предложенный срок
    status = models.CharField(max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'отклик'
        verbose_name_plural = 'отклики'
        ordering = ['-created_at']
        unique_together = ('job', 'specialist')   # один специалист — один отклик на вакансию

    def __str__(self):
        return f'{self.specialist} -> {self.job}'
