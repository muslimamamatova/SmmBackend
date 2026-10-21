"""Фильтры каталога вакансий для API."""

import django_filters

from apps.jobs.models import Job


class JobFilter(django_filters.FilterSet):
    """Набор фильтров: категория, география, бюджет, формат, навыки, статус."""

    category = django_filters.CharFilter(field_name='category')
    country = django_filters.CharFilter(field_name='country', lookup_expr='iexact')
    city = django_filters.CharFilter(field_name='city', lookup_expr='iexact')
    budget_min = django_filters.NumberFilter(field_name='budget_from', lookup_expr='gte')
    budget_max = django_filters.NumberFilter(field_name='budget_to', lookup_expr='lte')
    work_format = django_filters.CharFilter(field_name='work_format')
    status = django_filters.CharFilter(field_name='status')
    skills = django_filters.CharFilter(method='filter_skills')

    class Meta:
        model = Job
        fields = ['category', 'country', 'city', 'work_format', 'status', 'budget_type']

    def filter_skills(self, queryset, name, value):
        """Фильтрует по навыкам, переданным списком id: ``?skills=1,5,7``.

        Нечисловые значения отбрасываются, ``distinct()`` убирает дубли,
        которые даёт JOIN по many-to-many при совпадении нескольких навыков.
        """
        skill_ids = [part for part in value.split(',') if part.strip().isdigit()]
        if not skill_ids:
            return queryset
        return queryset.filter(skills__id__in=skill_ids).distinct()
