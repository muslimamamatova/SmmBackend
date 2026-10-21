"""Маршруты административного API."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.adminpanel.views import AdminComplaintViewSet, AdminDashboardView, AdminUserViewSet

router = DefaultRouter()
router.register('admin/users', AdminUserViewSet, basename='admin-user')
router.register('admin/complaints', AdminComplaintViewSet, basename='admin-complaint')

urlpatterns = [
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
] + router.urls
