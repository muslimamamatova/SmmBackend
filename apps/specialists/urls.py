"""Маршруты API специалистов: /specialists/ и вложенные экшены."""

from rest_framework.routers import DefaultRouter

from apps.specialists.views import SpecialistProfileViewSet

router = DefaultRouter()
# Роутер создаёт адреса: список, карточку, /me/, /{id}/reviews/, /{id}/verify/ и т. д.
router.register('specialists', SpecialistProfileViewSet, basename='specialist')

urlpatterns = router.urls
