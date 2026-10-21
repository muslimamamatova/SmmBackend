"""
Общие справочники значений (enum-ы), которые используют сразу несколько приложений.

Каждый класс — это набор пар «значение в базе» → «подпись для человека».
Подписи на русском сразу попадают и в админку, и в формы сайта, и в API
(через поля вида ``status_display``).

Хранить их в одном месте важно: например, специализация нужна и профилю
специалиста, и вакансии, и кейсу портфолио — так списки не разъезжаются.
"""

from django.db import models


class Specialization(models.TextChoices):
    """Специализация: кем работает специалист / кого ищет вакансия / к какой
    категории относится кейс в портфолио."""

    SMM_MANAGER = 'smm_manager', 'SMM-менеджер'
    CONTENT_MANAGER = 'content_manager', 'Контент-менеджер'
    TARGETOLOGIST = 'targetologist', 'Таргетолог'
    COPYWRITER = 'copywriter', 'Копирайтер'
    CONTENT_CREATOR = 'content_creator', 'Контент-мейкер'
    REELS_MAKER = 'reels_maker', 'Reels-мейкер'
    VIDEOGRAPHER = 'videographer', 'Видеограф'
    PHOTOGRAPHER = 'photographer', 'Фотограф'
    GRAPHIC_DESIGNER = 'graphic_designer', 'Графический дизайнер'
    MOTION_DESIGNER = 'motion_designer', 'Моушн-дизайнер'
    TIKTOK_SPECIALIST = 'tiktok_specialist', 'TikTok-специалист'
    INSTAGRAM_SPECIALIST = 'instagram_specialist', 'Instagram-специалист'
    TELEGRAM_SPECIALIST = 'telegram_specialist', 'Telegram-специалист'
    INFLUENCER_MANAGER = 'influencer_manager', 'Инфлюенс-менеджер'
    MARKETING_SPECIALIST = 'marketing_specialist', 'Маркетолог'
    SEO_SPECIALIST = 'seo_specialist', 'SEO-специалист'
    OTHER = 'other', 'Другое'


class WorkFormat(models.TextChoices):
    """Формат работы: удалённо, в офисе или смешанно."""

    REMOTE = 'remote', 'Удалённо'
    ONSITE = 'onsite', 'Очно'
    HYBRID = 'hybrid', 'Гибридный формат'


class ProfileStatus(models.TextChoices):
    """Уровень профиля специалиста — «значок доверия» на карточке.

    NEWBIE ставится автоматически при создании профиля, VERIFIED — после
    проверки модератором, TOP и PRO выдаются вручную.
    """

    NEWBIE = 'newbie', 'Новичок'
    VERIFIED = 'verified', 'Проверенный специалист'
    TOP = 'top', 'Топ-специалист'
    PRO = 'pro', 'PRO'


class BudgetType(models.TextChoices):
    """Как указан бюджет вакансии: точная сумма, диапазон или «по договорённости»."""

    FIXED = 'fixed', 'Фиксированная цена'
    RANGE = 'range', 'Диапазон бюджета'
    NEGOTIABLE = 'negotiable', 'По договорённости'


class JobStatus(models.TextChoices):
    """Жизненный цикл вакансии.

    DRAFT → OPEN (видна в поиске) → IN_PROGRESS (отклик принят, открыта сделка)
    → CLOSED. CANCELLED — снята автором или модератором.
    """

    DRAFT = 'draft', 'Черновик'
    OPEN = 'open', 'Открыта'
    IN_PROGRESS = 'in_progress', 'В работе'
    CLOSED = 'closed', 'Закрыта'
    CANCELLED = 'cancelled', 'Отменена'


class ApplicationStatus(models.TextChoices):
    """Статус отклика специалиста на вакансию.

    PENDING → ACCEPTED (заказчик согласился, создаётся сделка) или REJECTED.
    WITHDRAWN — специалист сам отозвал отклик.
    """

    PENDING = 'pending', 'На рассмотрении'
    ACCEPTED = 'accepted', 'Принят'
    REJECTED = 'rejected', 'Отклонён'
    WITHDRAWN = 'withdrawn', 'Отозван'


class OrderStatus(models.TextChoices):
    """Статус сделки (заказа) — основной «конвейер» работы на площадке.

    NEW/DISCUSSION → ACCEPTED (специалист принял) → IN_PROGRESS (начал работу)
    → REVIEW (сдал на проверку) → COMPLETED (заказчик принял, можно оставить отзыв).
    CANCELLED доступен до завершения. Допустимые переходы заданы в
    apps/orders/services.py.
    """

    NEW = 'new', 'Новый'
    DISCUSSION = 'discussion', 'Обсуждение'
    ACCEPTED = 'accepted', 'Принят'
    IN_PROGRESS = 'in_progress', 'В работе'
    REVIEW = 'review', 'На проверке'
    COMPLETED = 'completed', 'Завершён'
    CANCELLED = 'cancelled', 'Отменён'


class FavoriteType(models.TextChoices):
    """Что именно пользователь добавил в избранное.

    Модель Favorite хранит пару «тип + id», поэтому одним списком можно
    сохранять объекты разных таблиц.
    """

    SPECIALIST = 'specialist', 'Специалист'
    COMPANY = 'company', 'Компания'
    JOB = 'job', 'Вакансия'
    PORTFOLIO = 'portfolio', 'Портфолио'


class NotificationType(models.TextChoices):
    """Повод для уведомления — определяет иконку и текст в списке «Уведомления»."""

    APPLICATION = 'application', 'Новый отклик'
    MESSAGE = 'message', 'Новое сообщение'
    ORDER_STATUS = 'order_status', 'Статус заказа изменён'
    REVIEW = 'review', 'Новый отзыв'
    INVITATION = 'invitation', 'Приглашение'
    JOB_MATCH = 'job_match', 'Рекомендованная вакансия'


class ComplaintTargetType(models.TextChoices):
    """На что жалуется пользователь (тип объекта в жалобе)."""

    SPECIALIST = 'specialist', 'Профиль специалиста'
    COMPANY = 'company', 'Компания'
    PORTFOLIO = 'portfolio', 'Элемент портфолио'
    JOB = 'job', 'Вакансия'
    MESSAGE = 'message', 'Сообщение'
    REVIEW = 'review', 'Отзыв'


class ComplaintReason(models.TextChoices):
    """Причина жалобы — выбирается пользователем из списка."""

    FRAUD = 'fraud', 'Мошенничество'
    SPAM = 'spam', 'Спам'
    FAKE_PROFILE = 'fake_profile', 'Фейковый профиль'
    RULES_VIOLATION = 'rules_violation', 'Нарушение правил'
    PLAGIARISM = 'plagiarism', 'Плагиат'
    INAPPROPRIATE_CONTENT = 'inappropriate_content', 'Недопустимый контент'
    OTHER = 'other', 'Другое'


class ComplaintStatus(models.TextChoices):
    """Состояние обработки жалобы модератором."""

    PENDING = 'pending', 'На рассмотрении'
    RESOLVED = 'resolved', 'Решена'
    REJECTED = 'rejected', 'Отклонена'
