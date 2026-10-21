"""
Модели пользователей.

Основное:

* :class:`User` — своя модель пользователя: вход по email (не по username)
  и роль, которая определяет, что человек может делать на площадке;
* :class:`EmailOTP` — одноразовые коды подтверждения email при регистрации.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    """Роль пользователя — от неё зависят доступные разделы и права.

    * SPECIALIST — исполнитель: заполняет профиль специалиста, портфолио,
      откликается на вакансии;
    * EMPLOYER — заказчик: создаёт компанию, публикует вакансии, открывает сделки;
    * ADMIN — модератор площадки: видит панель, блокирует пользователей,
      разбирает жалобы.
    """

    SPECIALIST = 'specialist', 'Специалист'
    EMPLOYER = 'employer', 'Компания'
    ADMIN = 'admin', 'Администратор'


class UserStatus(models.TextChoices):
    """Статус аккаунта. BLOCKED полностью запрещает вход (и на сайт, и в API)."""

    ACTIVE = 'active', 'Активен'
    BLOCKED = 'blocked', 'Заблокирован'


class UserManager(BaseUserManager):
    """Менеджер создания пользователей с email вместо username.

    Стандартный ``UserManager`` Django требует username, которого у нас нет,
    поэтому методы создания переопределены.
    """

    # Разрешает использовать менеджер внутри миграций (например, для data-миграций).
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Общая часть создания пользователя: нормализация email и хеш пароля.

        Аргументы:
            email: обязателен, служит логином;
            password: сырой пароль, сохраняется только в виде хеша;
            extra_fields: любые другие поля модели (name, role, ...).

        Исключения:
            ValueError — если email не передан.
        """
        if not email:
            raise ValueError('Email is required')
        # Приводим домен к нижнему регистру, чтобы A@Mail.ru и a@mail.ru
        # не стали разными аккаунтами.
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        # set_password хеширует пароль (в базе сырой пароль не хранится).
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Создаёт обычного пользователя (без доступа в админку Django)."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Создаёт суперпользователя — вызывается командой `createsuperuser`.

        Помимо флагов доступа в админку сразу ставит роль «Администратор»,
        чтобы человек увидел и панель модерации на самом сайте.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.ADMIN)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Пользователь площадки: заказчик, специалист или администратор.

    Отличия от стандартной модели Django:

    * поле ``username`` удалено, логином служит ``email``;
    * добавлены ``role`` (что человек может делать) и ``status`` (активен/заблокирован);
    * ``status`` — единственный источник правды о блокировке: поле ``is_active``
      автоматически синхронизируется с ним в :meth:`save`.
    """

    username = None                                                 # логина-username нет
    email = models.EmailField(unique=True)                          # логин и адрес для писем
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    name = models.CharField(max_length=150)                         # отображаемое имя
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.EMPLOYER)
    status = models.CharField(max_length=20, choices=UserStatus.choices, default=UserStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)            # дата регистрации

    # Django использует это поле как логин при authenticate().
    USERNAME_FIELD = 'email'
    # Поля, которые дополнительно спрашивает команда createsuperuser.
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'пользователи'
        ordering = ['-created_at']

    def __str__(self):
        """Email — самое узнаваемое представление в админке и логах."""
        return self.email

    def save(self, *args, **kwargs):
        """Сохраняет пользователя, синхронизируя ``is_active`` со ``status``.

        Зачем: проверку «активен ли аккаунт» делают и сессионный вход, и
        SimpleJWT, и админка — все они смотрят на ``is_active``. Поэтому при
        блокировке (``status=blocked``) флаг снимается автоматически, и
        заблокированный пользователь не может войти ни одним способом.

        Отдельно обрабатывается ``update_fields``: если вызывающий код сохраняет
        только часть полей (например ``save(update_fields=['status'])``), поле
        ``is_active`` добавляется в список — иначе синхронизация не попала бы в базу.
        """
        self.is_active = self.status == UserStatus.ACTIVE

        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            kwargs['update_fields'] = set(update_fields) | {'is_active'}

        super().save(*args, **kwargs)

    @property
    def is_blocked(self):
        """True, если аккаунт заблокирован модератором."""
        return self.status == UserStatus.BLOCKED


class EmailOTP(models.Model):
    """Одноразовый код подтверждения email (6 цифр), который высылается письмом.

    Используется при регистрации через веб-интерфейс: пользователь создаётся
    только после ввода верного кода, до этого данные лежат в сессии.
    """

    email = models.EmailField(db_index=True)        # кому выслан код
    code = models.CharField(max_length=6)           # сам код, 6 цифр
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()             # после этого момента код недействителен
    is_used = models.BooleanField(default=False)    # повторно использовать код нельзя

    class Meta:
        verbose_name = 'код подтверждения email'
        verbose_name_plural = 'коды подтверждения email'
        ordering = ['-created_at']
        # Индекс под основной запрос: «последний код для этого email».
        indexes = [models.Index(fields=['email', '-created_at'])]

    def __str__(self):
        return f'OTP for {self.email}'

    def is_valid(self):
        """Проверяет, можно ли ещё использовать код: не использован и не истёк."""
        return not self.is_used and timezone.now() <= self.expires_at

    def mark_used(self):
        """Помечает код использованным, чтобы его нельзя было применить дважды."""
        self.is_used = True
        self.save(update_fields=['is_used'])

    @classmethod
    def generate(cls, email, ttl_minutes=None):
        """Создаёт новый код для email и гасит все предыдущие неиспользованные.

        Гашение старых кодов важно: иначе у пользователя одновременно
        действовало бы несколько кодов, и перехваченный старый код оставался бы
        рабочим после повторной отправки.

        Аргументы:
            email: адрес получателя;
            ttl_minutes: сколько минут живёт код; по умолчанию берётся из
                settings.OTP_TTL_MINUTES.

        Возвращает:
            Созданный объект :class:`EmailOTP` (его ``code`` нужно отправить письмом).
        """
        if ttl_minutes is None:
            ttl_minutes = getattr(settings, 'OTP_TTL_MINUTES', 10)

        # Все прежние активные коды этого адреса больше не действуют.
        cls.objects.filter(email=email, is_used=False).update(is_used=True)

        # secrets (а не random) — криптографически стойкий генератор,
        # код подтверждения предсказуемым быть не должен.
        code = f'{secrets.randbelow(1_000_000):06d}'
        return cls.objects.create(
            email=email,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )
