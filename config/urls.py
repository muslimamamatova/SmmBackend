"""
Корневая таблица маршрутов проекта.

Здесь собираются три группы URL:

* веб-сайт на Django-шаблонах (``apps.site``) — висит на корне «/»;
* админка Django — «/admin/»;
* REST API и его документация — «/api/v1/...» и плоские пути вроде «/jobs/».
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    # --- Веб-интерфейс (HTML-страницы на Django-шаблонах) -----------------
    # Подключён первым, поэтому «/» отдаёт главную страницу сайта.
    path('', include('apps.site.urls')),

    # --- Стандартная админка Django ---------------------------------------
    path('admin/', admin.site.urls),

    # --- Документация API -------------------------------------------------
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),              # OpenAPI JSON/YAML
    path('api/v1/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Административное API держим под /api/v1/, чтобы его пути (/admin/users/
    # и т. п.) не конфликтовали с админкой Django выше.
    path('api/v1/', include('apps.adminpanel.urls')),

    # --- Публичное REST API -----------------------------------------------
    # Каждое приложение само описывает свои маршруты через DRF-роутер.
    path('', include('apps.users.urls')),         # /auth/register, /auth/login, /me
    path('', include('apps.common.urls')),        # /skills, /favorites, /notifications, /complaints
    path('', include('apps.companies.urls')),     # /companies
    path('', include('apps.specialists.urls')),   # /specialists
    path('', include('apps.portfolio.urls')),     # /portfolio
    path('', include('apps.jobs.urls')),          # /jobs, /applications
    path('', include('apps.orders.urls')),        # /orders, /reviews
    path('', include('apps.chat.urls')),          # /chats
]

# В режиме разработки Django сам раздаёт загруженные файлы (аватары, обложки).
# В продакшене это делает веб-сервер (nginx и т. п.).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
