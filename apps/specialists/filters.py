"""
Фильтры каталога специалистов для API.

Класс подключён во вьюсете через ``filterset_class`` и превращает параметры
строки запроса (``?specialization=copywriter&price_max=500``) в условия
SQL-выборки.
"""

import django_filters

from apps.specialists.models import SpecialistProfile


class SpecialistProfileFilter(django_filters.FilterSet):
    """Набор фильтров каталога: профессия, география, цена, рейтинг, навыки."""

    specialization = django_filters.CharFilter(field_name='specialization')
    # iexact — совпадение без учёта регистра: «Москва» = «москва».
    country = django_filters.CharFilter(field_name='country', lookup_expr='iexact')
    city = django_filters.CharFilter(field_name='city', lookup_expr='iexact')
    # gte/lte — «не меньше» / «не больше».
    experience_min = django_filters.NumberFilter(field_name='experience_years', lookup_expr='gte')
    price_min = django_filters.NumberFilter(field_name='price_from', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price_to', lookup_expr='lte')
    rating_min = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    work_format = django_filters.CharFilter(field_name='work_format')
    is_available = django_filters.BooleanFilter(field_name='is_available')
    # Нестандартные фильтры обрабатываются методами ниже.
    language = django_filters.CharFilter(method='filter_language')
    skills = django_filters.CharFilter(method='filter_skills')

    class Meta:
        model = SpecialistProfile
        fields = [
            'specialization', 'country', 'city', 'work_format', 'is_available',
            'verified', 'status',
        ]

    def filter_language(self, queryset, name, value):
        """Оставляет специалистов, у которых в списке языков есть искомый.

        Языки хранятся в JSON-поле, поэтому используется поиск по подстроке —
        простой вариант, работающий и на SQLite, и на PostgreSQL.
        """
        return queryset.filter(languages__icontains=value)

    def filter_skills(self, queryset, name, value):
        """Фильтрует по навыкам, переданным списком id: ``?skills=1,5,7``.

        Нечисловые значения игнорируются (защита от мусора в параметре), а
        ``distinct()`` убирает дубли, которые даёт JOIN по many-to-many, когда
        у специалиста совпало несколько навыков сразу.
        """
        skill_ids = [part for part in value.split(',') if part.strip().isdigit()]
        if not skill_ids:
            return queryset
        return queryset.filter(skills__id__in=skill_ids).distinct()
