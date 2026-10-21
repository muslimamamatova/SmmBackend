"""Маршруты API чата."""

from rest_framework.routers import DefaultRouter

from apps.chat.views import ChatViewSet

router = DefaultRouter()
router.register('chats', ChatViewSet, basename='chat')

urlpatterns = router.urls
