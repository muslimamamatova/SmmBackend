"""Отображение профилей специалистов в админке."""

from django.contrib import admin

from apps.specialists.models import SpecialistProfile


@admin.register(SpecialistProfile)
class SpecialistProfileAdmin(admin.ModelAdmin):
    """Список профилей с фильтрами по профессии и статусу проверки.

    Поля репутации только для чтения: они считаются автоматически из отзывов
    и завершённых сделок (apps/orders/services.py), и ручная правка их сломает.
    """

    list_display = ['id', 'user', 'specialization', 'status', 'verified', 'rating', 'orders_count', 'created_at']
    list_filter = ['specialization', 'status', 'verified', 'work_format']
    search_fields = ['user__name', 'user__email', 'city', 'country']
    filter_horizontal = ['skills']
    readonly_fields = ['rating', 'reviews_count', 'orders_count', 'created_at', 'updated_at']
