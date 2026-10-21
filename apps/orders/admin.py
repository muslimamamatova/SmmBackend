"""Отображение сделок и отзывов в админке."""

from django.contrib import admin

from apps.orders.models import Order, Review


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Сделки с фильтром по статусу — основной инструмент разбора споров."""

    list_display = ['id', 'company', 'specialist', 'price', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['company__name', 'specialist__user__name']
    readonly_fields = ['started_at', 'completed_at', 'created_at', 'updated_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Отзывы участников сделок."""

    list_display = ['id', 'order', 'author', 'recipient', 'rating', 'created_at']
    search_fields = ['author__email', 'recipient__email']
