"""Отображение компаний в админке."""

from django.contrib import admin

from apps.companies.models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Список компаний с поиском по названию и email владельца."""

    list_display = ['id', 'name', 'user', 'industry', 'city', 'country', 'created_at']
    list_filter = ['industry']
    search_fields = ['name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
