"""Маршруты API компаний: /companies/ и /companies/me/."""

from rest_framework.routers import DefaultRouter

from apps.companies.views import CompanyViewSet

router = DefaultRouter()
router.register('companies', CompanyViewSet, basename='company')

urlpatterns = router.urls
