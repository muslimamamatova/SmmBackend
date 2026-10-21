"""
Общие модели, которые используются всеми разделами площадки:

* :class:`Skill` — справочник навыков (теги для профилей и вакансий);
* :class:`Favorite` — избранное пользователя;
* :class:`Notification` — уведомления внутри сайта;
* :class:`Complaint` — жалобы на контент и их разбор модератором.
"""

from django.conf import settings
from django.db import models

from apps.common.choices import ComplaintReason, ComplaintStatus, ComplaintTargetType, FavoriteType, NotificationType


class Skill(models.Model):
    """Навык из общего справочника, например «Reels» или «Яндекс.Директ».

    Привязывается к профилям специалистов и к вакансиям через
    ManyToMany-поля, что позволяет искать «кто умеет X» и «куда нужен X».
    """

    name = models.CharField(max_length=60, unique=True)   # уникальное название навыка

    class Meta:
        verbose_name = 'навык'
        verbose_name_plural = 'навыки'
        ordering = ['name']   # по алфавиту — так удобнее в выпадающих списках

    def __str__(self):
        return self.name


class Favorite(models.Model):
    """Запись «пользователь сохранил объект» для раздела «Избранное».

    Вместо отдельной таблицы под каждый тип объекта хранится пара
    ``object_type`` + ``object_id``. Это проще, но у поля нет внешнего ключа,
    поэтому при удалении самого объекта запись в избранном остаётся «висеть» —
    представления (views) просто не находят её по id и не показывают.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    object_type = models.CharField(max_length=20, choices=FavoriteType.choices)   # специалист/вакансия/...
    object_id = models.PositiveIntegerField()                                     # id объекта этого типа
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'избранное'
        verbose_name_plural = 'избранное'
        # Один и тот же объект нельзя добавить в избранное дважды.
        unique_together = ('user', 'object_type', 'object_id')
        ordering = ['-created_at']   # сначала недавно добавленные

    def __str__(self):
        return f'{self.user} -> {self.object_type}:{self.object_id}'


class Notification(models.Model):
    """Уведомление пользователю: новый отклик, сообщение, смена статуса сделки.

    Создаётся через вспомогательную функцию ``apps.site.views.notify``.
    Поле ``link`` хранит относительный URL, по которому пользователь попадает
    к источнику события.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=NotificationType.choices)   # повод
    title = models.CharField(max_length=255)                                   # заголовок в списке
    text = models.TextField(blank=True)                                        # подробности
    link = models.CharField(max_length=255, blank=True)                        # куда перейти
    is_read = models.BooleanField(default=False)                               # для бейджа в меню
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'уведомление'
        verbose_name_plural = 'уведомления'
        ordering = ['-created_at']
        # Индекс под главный запрос: «непрочитанные уведомления пользователя».
        indexes = [models.Index(fields=['user', 'is_read'])]

    def __str__(self):
        return f'{self.type} -> {self.user}'


class Complaint(models.Model):
    """Жалоба пользователя на объект площадки и результат её разбора.

    Путь жалобы: пользователь отправляет её со страницы объекта
    (``status=PENDING``) → модератор в панели решает «Решена» или «Отклонена»,
    при этом записываются ``resolved_by``, ``resolved_at`` и комментарий.

    Как и в :class:`Favorite`, объект описан парой «тип + id» без внешнего ключа.
    """

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='complaints_filed',
    )  # кто пожаловался
    target_type = models.CharField(max_length=20, choices=ComplaintTargetType.choices)   # на что
    target_id = models.PositiveIntegerField()                                            # id объекта
    reason = models.CharField(max_length=30, choices=ComplaintReason.choices)            # причина
    comment = models.TextField(blank=True)                                               # пояснение автора

    # --- Поля модерации -----------------------------------------------------
    status = models.CharField(max_length=20, choices=ComplaintStatus.choices, default=ComplaintStatus.PENDING)
    moderator_comment = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='complaints_resolved',
    )  # SET_NULL: удаление аккаунта модератора не должно удалять историю жалоб
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'жалоба'
        verbose_name_plural = 'жалобы'
        ordering = ['-created_at']
        # Индекс под очередь модерации: «жалобы в статусе PENDING».
        indexes = [models.Index(fields=['status', '-created_at'])]

    def __str__(self):
        return f'{self.reason} -> {self.target_type}:{self.target_id}'
