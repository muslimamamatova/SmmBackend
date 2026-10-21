"""Маршруты API вакансий и откликов."""

from rest_framework.routers import DefaultRouter

from apps.jobs.views import ApplicationViewSet, JobViewSet

router = DefaultRouter()
router.register('jobs', JobViewSet, basename='job')                       # /jobs/, /jobs/{id}/applications/, ...
router.register('applications', ApplicationViewSet, basename='application')  # /applications/{id}/accept/, ...

urlpatterns = router.urls
