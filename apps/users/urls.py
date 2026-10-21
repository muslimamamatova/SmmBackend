"""Маршруты авторизации REST API."""

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.views import LogoutView, MeView, RegisterView

urlpatterns = [
    # Регистрация: создаёт пользователя и возвращает токены.
    path('auth/register', RegisterView.as_view(), name='auth-register'),
    # Вход: email + пароль -> пара токенов (готовая вьюха simplejwt).
    path('auth/login', TokenObtainPairView.as_view(), name='auth-login'),
    # Продление сессии: refresh -> новый access (и новый refresh, т.к. включена ротация).
    path('auth/refresh', TokenRefreshView.as_view(), name='auth-refresh'),
    # Выход: отзыв refresh-токена.
    path('auth/logout', LogoutView.as_view(), name='auth-logout'),
    # Текущий пользователь: чтение и частичное обновление профиля.
    path('me', MeView.as_view(), name='me'),
]
