"""
Настройки Django-проекта «SMM Marketplace».

Проект состоит из двух частей, которые работают на одном Django-приложении:

1. REST API (Django REST Framework + JWT) — для мобильных/внешних клиентов,
   схема доступна по /api/v1/swagger/;
2. Веб-интерфейс на Django-шаблонах (приложение ``apps.site``) — обычные
   HTML-страницы с сессионной авторизацией, доступны с корня сайта «/».

Все значения, зависящие от окружения (секретный ключ, база данных, почта),
читаются из файла .env через python-decouple — образец см. в .env.example.
"""

from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

# Корень проекта — папка, в которой лежит manage.py.
# Используется для построения путей вида BASE_DIR / 'templates'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Базовая безопасность
# ---------------------------------------------------------------------------

# Секретный ключ подписи сессий и токенов. В продакшене ОБЯЗАТЕЛЬНО задать
# свой в .env — значение по умолчанию только для локальной разработки.
SECRET_KEY = config('SECRET_KEY', default='django-insecure-gz_u--o@-+aq!=z$kbt&91e+k9*r*9r9dbmzgr!2@yu=3xtz_k')

# Режим отладки: показывает трейсбеки и отдаёт media-файлы напрямую.
# На сервере должно быть DEBUG=False.
DEBUG = config('DEBUG', default=True, cast=bool)

# Домены, с которых разрешено принимать запросы (защита от Host-header атак).
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Домены, которым доверяем при проверке CSRF-токена POST-форм. Заполняется,
# когда сайт работает за HTTPS-прокси или на своём домене, например:
# CSRF_TRUSTED_ORIGINS=https://smm.example.com
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())


# ---------------------------------------------------------------------------
# Приложения
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    # Стандартные приложения Django.
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Сторонние библиотеки.
    'rest_framework',                               # REST API
    'rest_framework_simplejwt',                     # JWT-токены
    'rest_framework_simplejwt.token_blacklist',     # чёрный список refresh-токенов (logout)
    'corsheaders',                                  # CORS для внешних клиентов
    'django_filters',                               # фильтрация списков в API
    'drf_spectacular',                              # генерация OpenAPI-схемы

    # Приложения проекта (бизнес-логика и API).
    'apps.users',         # пользователи, регистрация, авторизация, OTP-коды
    'apps.common',        # справочники, избранное, уведомления, жалобы
    'apps.specialists',   # профили специалистов
    'apps.companies',     # профили компаний-заказчиков
    'apps.portfolio',     # кейсы специалистов (портфолио)
    'apps.jobs',          # вакансии и отклики на них
    'apps.orders',        # сделки (заказы) и отзывы
    'apps.chat',          # чаты и сообщения
    'apps.adminpanel',    # административное API (модерация, статистика)

    # Веб-интерфейс на Django-шаблонах.
    'apps.site',
]

# Своя модель пользователя: вход по email, роль (специалист/компания/админ).
AUTH_USER_MODEL = 'users.User'

# Куда отправлять неавторизованных и куда редиректить после входа/выхода
# в веб-части сайта.
LOGIN_URL = 'site:login'
LOGIN_REDIRECT_URL = 'site:dashboard'
LOGOUT_REDIRECT_URL = 'site:home'


# ---------------------------------------------------------------------------
# Middleware (обработчики запроса/ответа; порядок важен)
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',            # заголовки безопасности
    'corsheaders.middleware.CorsMiddleware',                    # CORS, должен идти до CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',     # сессии
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',                # защита POST-форм
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # добавляет request.user
    'django.contrib.messages.middleware.MessageMiddleware',     # flash-сообщения
    'django.middleware.clickjacking.XFrameOptionsMiddleware',   # защита от встраивания в iframe
]

ROOT_URLCONF = 'config.urls'


# ---------------------------------------------------------------------------
# Шаблоны (HTML-фронтенд)
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Общая папка шаблонов проекта + шаблоны внутри приложений
        # (apps/site/templates/site/*.html).
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',          # переменная user
                'django.contrib.messages.context_processors.messages',  # переменная messages
                # Свой процессор: счётчики непрочитанных сообщений,
                # уведомлений и жалоб для бейджей в меню.
                'apps.site.context_processors.unread_messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# ---------------------------------------------------------------------------
# База данных
# ---------------------------------------------------------------------------
# По умолчанию SQLite — для локального запуска ничего настраивать не нужно.
# Для продакшена в .env указывают DB_ENGINE=postgres и параметры подключения.

if config('DB_ENGINE', default='sqlite') == 'postgres':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='smm_marketplace'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            # Держим соединение открытым N секунд вместо переподключения на
            # каждый запрос — заметно быстрее под нагрузкой.
            'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=60, cast=int),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ---------------------------------------------------------------------------
# Пароли и авторизация
# ---------------------------------------------------------------------------
# Набор проверок: пароль не похож на email/имя, не короче 8 символов,
# не из списка популярных и не состоит только из цифр.

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Бэкенд авторизации проекта: как стандартный ModelBackend, но дополнительно
# запрещает вход пользователям со статусом «Заблокирован».
AUTHENTICATION_BACKENDS = ['apps.users.backends.ActiveStatusModelBackend']


# ---------------------------------------------------------------------------
# Локализация
# ---------------------------------------------------------------------------

LANGUAGE_CODE = config('LANGUAGE_CODE', default='ru-ru')   # язык админки, форм и ошибок
TIME_ZONE = config('TIME_ZONE', default='UTC')             # часовой пояс отображения
USE_I18N = True                                            # включить переводы
USE_TZ = True                                              # хранить даты в UTC


# ---------------------------------------------------------------------------
# Статика и медиа
# ---------------------------------------------------------------------------

STATIC_URL = 'static/'
# Куда `manage.py collectstatic` соберёт файлы для раздачи веб-сервером.
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Загруженные пользователями файлы: аватары, обложки кейсов, вложения чата.
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Тип первичного ключа по умолчанию для всех моделей.
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    # Аутентификация по JWT в заголовке `Authorization: Bearer <access>`.
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    # По умолчанию читать может любой, изменять — только авторизованный;
    # отдельные вьюсеты уточняют это в get_permissions().
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    # Фильтрация (?category=...), поиск (?search=...) и сортировка (?ordering=...).
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    # Постраничная выдача списков: ?page=2.
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    # Генератор OpenAPI-схемы.
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Настройки документации (Swagger UI / Redoc).
SPECTACULAR_SETTINGS = {
    'TITLE': 'SMM Marketplace API',
    'DESCRIPTION': 'API маркетплейса SMM-специалистов: вакансии, сделки, специалисты, компании, портфолио и чат.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    # Явное имя enum-а, чтобы схема не ругалась на одинаковые наборы значений.
    'ENUM_NAME_OVERRIDES': {
        'SpecializationEnum': 'apps.common.choices.Specialization',
    },
    # Убирает префикс /api/v1 из путей в документации (см. config/openapi.py).
    'PREPROCESSING_HOOKS': ['config.openapi.strip_api_v1_prefix'],
}

# Время жизни и правила ротации JWT-токенов.
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),   # короткий токен доступа
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),     # долгий токен обновления
    'ROTATE_REFRESH_TOKENS': True,                    # выдавать новый refresh при обновлении
    'BLACKLIST_AFTER_ROTATION': True,                 # старый refresh становится недействительным
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS: в разработке разрешаем запросы с любого origin, в продакшене
# выставляют CORS_ALLOW_ALL_ORIGINS=False и список CORS_ALLOWED_ORIGINS.
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=True, cast=bool)
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='', cast=Csv())


# ---------------------------------------------------------------------------
# Почта (используется для OTP-кодов при регистрации)
# ---------------------------------------------------------------------------
# По умолчанию письма печатаются в консоль runserver — удобно для разработки.
# Для реальной отправки в .env задают EMAIL_BACKEND=...smtp.EmailBackend
# и параметры SMTP-сервера.

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@smm-marketplace.local')

# Сколько минут живёт код подтверждения email.
OTP_TTL_MINUTES = config('OTP_TTL_MINUTES', default=10, cast=int)


# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------
# Всё пишется в консоль. Уровни настраиваются через .env, чтобы включить
# подробный вывод без правки кода.

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': config('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        # Логгер проекта: logging.getLogger('smm') в коде приложений.
        'smm': {
            'handlers': ['console'],
            'level': config('APP_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
    },
}


# ---------------------------------------------------------------------------
# Дополнительная защита для продакшена
# ---------------------------------------------------------------------------
# Включается автоматически при DEBUG=False, чтобы случайно не выложить сайт
# с «разработческими» настройками.

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True                 # запретить угадывание MIME-типа
    X_FRAME_OPTIONS = 'DENY'                           # запретить встраивание в iframe
    SESSION_COOKIE_HTTPONLY = True                     # cookie сессии недоступна из JS
    SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
    CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
    # Редирект на HTTPS и HSTS — включать, когда уже настроен сертификат.
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Доверять заголовку прокси о том, что исходный запрос пришёл по HTTPS.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
