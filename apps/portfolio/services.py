"""
Сервисный слой портфолио — операции, которые нужны и REST API, и веб-сайту.

Логика лайков и просмотров живёт здесь, чтобы не дублироваться в
``apps/portfolio/views.py`` (API) и ``apps/site/views.py`` (HTML-страницы)
и чтобы счётчики везде обновлялись одинаково.
"""

from django.db.models import F

from apps.portfolio.models import Portfolio, PortfolioLike


def register_view(portfolio):
    """Увеличивает счётчик просмотров кейса на единицу.

    Инкремент делается выражением ``F('views_count') + 1``, то есть прямо в
    SQL (``UPDATE ... SET views_count = views_count + 1``). Это важно: если
    читать значение в Python и записывать обратно, два одновременных просмотра
    затрут друг друга и один из них потеряется.

    Аргументы:
        portfolio: объект кейса; его поле ``views_count`` обновляется и
            перечитывается из базы, чтобы шаблон показал актуальное число.
    """
    Portfolio.objects.filter(pk=portfolio.pk).update(views_count=F('views_count') + 1)
    portfolio.refresh_from_db(fields=['views_count'])


def toggle_like(portfolio, user):
    """Ставит или снимает лайк пользователя на кейсе.

    Работает как переключатель: если лайка не было — создаёт его и увеличивает
    счётчик, если был — удаляет и уменьшает. Уникальность пары
    (кейс, пользователь) гарантирует сама модель, поэтому двойных лайков
    быть не может.

    Аргументы:
        portfolio: кейс, который лайкают;
        user: авторизованный пользователь.

    Возвращает:
        bool — True, если лайк в итоге стоит, False, если он снят. Значение
        используется и для ответа API, и для подсветки кнопки в шаблоне.
    """
    like, created = PortfolioLike.objects.get_or_create(portfolio=portfolio, user=user)

    if created:
        # Лайк поставлен впервые.
        Portfolio.objects.filter(pk=portfolio.pk).update(likes_count=F('likes_count') + 1)
        liked = True
    else:
        # Повторное нажатие — снимаем лайк.
        like.delete()
        # greatest-защита не нужна: счётчик уменьшается ровно столько раз,
        # сколько лайков было создано, но на всякий случай не даём уйти ниже нуля.
        Portfolio.objects.filter(pk=portfolio.pk, likes_count__gt=0).update(likes_count=F('likes_count') - 1)
        liked = False

    portfolio.refresh_from_db(fields=['likes_count'])
    return liked
