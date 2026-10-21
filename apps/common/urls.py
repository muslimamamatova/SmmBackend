"""
Маршруты общих разделов API.

DefaultRouter сам разворачивает каждый вьюсет в набор адресов:
``/skills/``, ``/skills/{id}/`` и т. д., включая методы-экшены
вида ``/notifications/read-all/``.
"""

from rest_framework.routers import DefaultRouter

from apps.common.views import ComplaintViewSet, FavoriteViewSet, NotificationViewSet, SkillViewSet

router = DefaultRouter()
router.register('skills', SkillViewSet, basename='skill')                    # справочник навыков
router.register('favorites', FavoriteViewSet, basename='favorite')           # избранное
router.register('notifications', NotificationViewSet, basename='notification')  # уведомления
router.register('complaints', ComplaintViewSet, basename='complaint')        # жалобы пользователя

urlpatterns = router.urls
