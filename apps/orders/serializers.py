"""Сериализаторы сделок и отзывов."""

from rest_framework import serializers

from apps.orders.models import Order, Review


class OrderSerializer(serializers.ModelSerializer):
    """Сделка для API.

    ``company``, ``status`` и временные метки — только для чтения: компания
    подставляется из токена при создании, а статус меняется отдельными
    действиями (accept/start/submit/complete/cancel), а не произвольным PATCH.
    """

    company_name = serializers.CharField(source='company.name', read_only=True)
    specialist_name = serializers.CharField(source='specialist.user.name', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    has_review = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'job', 'job_title', 'company', 'company_name', 'specialist', 'specialist_name',
            'price', 'deadline', 'status', 'status_display', 'started_at', 'completed_at',
            'has_review', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'company', 'status', 'started_at', 'completed_at', 'created_at', 'updated_at']

    def get_has_review(self, obj) -> bool:
        """Есть ли уже отзыв по этой сделке (чтобы клиент не показывал форму повторно)."""
        return hasattr(obj, 'review')

    def create(self, validated_data):
        """Открывает сделку от имени компании текущего пользователя."""
        validated_data['company'] = self.context['request'].user.company
        return super().create(validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    """Отзыв об исполнителе/заказчике по завершённой сделке.

    ``order``, ``author`` и ``recipient`` только для чтения — все три
    вычисляются сервером в :meth:`create`, чтобы отзыв нельзя было подписать
    чужим именем или привязать к чужой сделке.
    """

    author_name = serializers.CharField(source='author.name', read_only=True)
    recipient_name = serializers.CharField(source='recipient.name', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'order', 'author', 'author_name', 'recipient', 'recipient_name', 'rating',
            'quality_rating', 'timeliness_rating', 'communication_rating', 'compliance_rating',
            'text', 'created_at',
        ]
        read_only_fields = ['id', 'order', 'author', 'recipient', 'created_at']

    def create(self, validated_data):
        """Определяет получателя отзыва по направлению: компания -> специалист или наоборот."""
        order = self.context['order']
        author = self.context['request'].user
        recipient = order.specialist.user if author == order.company.user else order.company.user

        validated_data['order'] = order
        validated_data['author'] = author
        validated_data['recipient'] = recipient
        return super().create(validated_data)
