"""
Сервисный слой вакансий и откликов.

Здесь живёт правило «что происходит при принятии отклика», общее для REST API
(``apps/jobs/views.py``) и веб-интерфейса (``apps/site/views.py``) — чтобы
при принятии отклика сделка создавалась одинаково в обоих случаях.
"""

from apps.common.choices import ApplicationStatus, JobStatus, OrderStatus


def accept_application(application):
    """Принимает отклик специалиста и открывает по нему сделку.

    Если на эту вакансию уже есть сделка с этим специалистом (например,
    отклик принимали повторно после сбоя), новая не создаётся — используется
    существующая, чтобы не задвоить работу.

    Аргументы:
        application: объект :class:`apps.jobs.models.Application`,
            который нужно перевести в статус «Принят».

    Возвращает:
        Кортеж ``(order, created)`` — сделка и флаг, была ли она создана
        только что (как в ``get_or_create``).
    """
    # Импорт внутри функции — иначе apps.jobs и apps.orders заимпортировали бы
    # друг друга на уровне модулей (apps.orders.models уже ссылается на Job).
    from apps.orders.models import Order

    application.status = ApplicationStatus.ACCEPTED
    application.save(update_fields=['status', 'updated_at'])

    job = application.job
    order, created = Order.objects.get_or_create(
        job=job,
        specialist=application.specialist,
        defaults={
            'company': job.company,
            'status': OrderStatus.NEW,
            # Цена и срок по умолчанию берутся из предложения специалиста,
            # а если он их не указал — из параметров самой вакансии.
            'price': application.price or job.budget_from or 0,
            'deadline': application.deadline or job.deadline,
        },
    )

    if created:
        # Вакансия закрывается для новых откликов — работа уже распределена.
        job.status = JobStatus.IN_PROGRESS
        job.save(update_fields=['status', 'updated_at'])

    return order, created


def reject_application(application):
    """Отклоняет отклик специалиста."""
    application.status = ApplicationStatus.REJECTED
    application.save(update_fields=['status', 'updated_at'])


def withdraw_application(application):
    """Отзывает отклик по инициативе самого специалиста."""
    application.status = ApplicationStatus.WITHDRAWN
    application.save(update_fields=['status', 'updated_at'])
