"""
Контекстный процессор веб-интерфейса.

Подключён в settings.TEMPLATES, поэтому его результат автоматически
добавляется в контекст КАЖДОГО шаблона — именно так в base.html появляются
переменные ``unread_messages_count`` и ``unread_alerts_count`` для бейджей
в верхнем меню, без необходимости передавать их из каждой вьюхи вручную.
"""

from apps.chat.models import Message
from apps.common.choices import ComplaintStatus
from apps.common.models import Complaint, Notification


def unread_messages(request):
    """Считает непрочитанные сообщения, уведомления и (для админа) жалобы.

    Для неавторизованного посетителя смысла в счётчиках нет, поэтому для
    него процессор отдаёт пустой словарь — в шаблоне теги
    ``{% if unread_messages_count %}`` просто не сработают.
    """
    if not request.user.is_authenticated:
        return {}

    context = {
        'unread_messages_count': Message.objects.filter(
            chat__participants=request.user, read_at__isnull=True,
        ).exclude(sender=request.user).count(),
        'unread_alerts_count': Notification.objects.filter(user=request.user, is_read=False).count(),
    }

    # Бейдж «жалобы на рассмотрении» нужен только администратору — это его
    # рабочая очередь, остальным пользователям жалобы не показываются.
    if request.user.role == 'admin':
        context['pending_complaints_count'] = Complaint.objects.filter(status=ComplaintStatus.PENDING).count()

    return context
