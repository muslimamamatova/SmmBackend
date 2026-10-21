"""Маршруты API портфолио: /portfolio/ и вложенные экшены (like, media)."""

from rest_framework.routers import DefaultRouter

from apps.portfolio.views import PortfolioViewSet

router = DefaultRouter()
router.register('portfolio', PortfolioViewSet, basename='portfolio')

urlpatterns = router.urls
