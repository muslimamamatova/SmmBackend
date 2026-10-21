"""Маршруты API сделок и отзывов."""

from rest_framework.routers import DefaultRouter

from apps.orders.views import OrderViewSet, ReviewViewSet

router = DefaultRouter()
router.register('orders', OrderViewSet, basename='order')     # /orders/{id}/accept/, /start/, /complete/, ...
router.register('reviews', ReviewViewSet, basename='review')  # публичный список отзывов

urlpatterns = router.urls
