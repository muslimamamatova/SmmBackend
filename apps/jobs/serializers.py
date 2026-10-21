"""Сериализаторы вакансий и откликов."""

from rest_framework import serializers

from apps.common.models import Skill
from apps.jobs.models import Application, Job
from apps.specialists.serializers import SpecialistProfileSerializer


class JobSerializer(serializers.ModelSerializer):
    """Вакансия для API.

    ``company`` и ``status`` только для чтения — компания подставляется из
    токена при создании, а статус меняется отдельными действиями
    (модерация, автоматическое закрытие при принятии отклика).
    """

    company_name = serializers.CharField(source='company.name', read_only=True)
    skills = serializers.PrimaryKeyRelatedField(queryset=Skill.objects.all(), many=True, required=False)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    applications_count = serializers.IntegerField(source='applications.count', read_only=True)

    class Meta:
        model = Job
        fields = [
            'id', 'company', 'company_name', 'title', 'description', 'category', 'category_display',
            'tasks', 'budget_type', 'budget_from', 'budget_to', 'deadline', 'work_format', 'country',
            'city', 'skills', 'status', 'status_display', 'applications_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'company', 'status', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Публикует вакансию от имени компании текущего пользователя."""
        validated_data['company'] = self.context['request'].user.company
        return super().create(validated_data)


class ApplicationSerializer(serializers.ModelSerializer):
    """Отклик специалиста на вакансию для API.

    ``job`` и ``specialist`` только для чтения — оба подставляются сервером
    (specialist — из токена, job — из URL), чтобы отклик нельзя было создать
    от имени другого специалиста или на чужую вакансию по ошибке в теле запроса.
    """

    specialist_detail = SpecialistProfileSerializer(source='specialist', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Application
        fields = [
            'id', 'job', 'job_title', 'specialist', 'specialist_detail', 'message', 'price',
            'deadline', 'status', 'status_display', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'job', 'specialist', 'status', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Создаёт отклик текущего специалиста на вакансию из контекста запроса."""
        user = self.context['request'].user
        validated_data['specialist'] = user.specialist_profile
        validated_data['job'] = self.context['job']
        return super().create(validated_data)
