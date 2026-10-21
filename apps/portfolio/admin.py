"""Отображение портфолио в админке."""

from django.contrib import admin

from apps.portfolio.models import Portfolio, PortfolioLike, PortfolioMedia


class PortfolioMediaInline(admin.TabularInline):
    """Файлы кейса редактируются прямо на странице кейса, без перехода в отдельный раздел."""

    model = PortfolioMedia
    extra = 1


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    """Кейсы портфолио с счётчиками популярности (только для просмотра)."""

    list_display = ['id', 'title', 'specialist', 'category', 'likes_count', 'views_count', 'created_at']
    list_filter = ['category']
    search_fields = ['title', 'specialist__user__name']
    inlines = [PortfolioMediaInline]
    readonly_fields = ['likes_count', 'views_count', 'created_at', 'updated_at']


@admin.register(PortfolioLike)
class PortfolioLikeAdmin(admin.ModelAdmin):
    """Лайки — в основном для отладки счётчиков."""

    list_display = ['id', 'portfolio', 'user', 'created_at']
