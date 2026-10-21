"""Отображение вакансий и откликов в админке."""

from django.contrib import admin

from apps.jobs.models import Application, Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """Список вакансий с фильтрами по статусу и категории."""

    list_display = ['id', 'title', 'company', 'category', 'status', 'budget_type', 'created_at']
    list_filter = ['status', 'category', 'budget_type', 'work_format']
    search_fields = ['title', 'company__name']
    filter_horizontal = ['skills']


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """Отклики специалистов на вакансии."""

    list_display = ['id', 'job', 'specialist', 'price', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['job__title', 'specialist__user__name']
