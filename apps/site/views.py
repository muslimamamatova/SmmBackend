"""
Веб-интерфейс площадки на Django-шаблонах.

Это «вторая сторона» проекта — те же данные, что отдаёт REST API, но в виде
обычных HTML-страниц с сессионной авторизацией. Чтобы бизнес-правила не
разъезжались между API и сайтом, вся логика переходов статусов и подобное
вынесена в сервисные функции приложений (``apps.orders.services``,
``apps.jobs.services``, ``apps.portfolio.services``, ``apps.chat.services``)
и здесь только вызывается.

Файл разбит на разделы комментариями-заголовками в порядке, в котором разделы
идут в apps/site/urls.py: главная → регистрация/вход → профиль → каталоги →
чат → портфолио → лента работ → избранное → уведомления → сделки → жалобы →
панель администратора.
"""

from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from rest_framework.exceptions import ValidationError

from apps.chat.models import Chat
from apps.chat.services import get_or_create_direct_chat, mark_messages_read
from apps.common.choices import (
    ComplaintStatus, ComplaintTargetType, FavoriteType, JobStatus, NotificationType, OrderStatus,
)
from apps.common.models import Complaint, Favorite, Notification
from apps.companies.models import Company
from apps.jobs.models import Application, Job
from apps.jobs.services import accept_application, reject_application
from apps.orders.models import Order, Review
from apps.orders.services import (
    accept_order, cancel_order, complete_order, refresh_specialist_rating, start_order, submit_order,
)
from apps.portfolio.models import Portfolio, PortfolioLike
# register_view переименован при импорте: ниже в файле уже есть HTML-вью
# register_view (шаг 1 регистрации пользователя) — имена не должны совпадать.
from apps.portfolio.services import register_view as register_portfolio_view, toggle_like
from apps.site.forms import (
    ApplicationForm, ComplaintForm, CompanyForm, JobFilterForm, JobForm, LoginForm, OTPForm,
    PortfolioForm, RegisterForm, ReviewForm, SpecialistFilterForm, SpecialistProfileForm, WorksFilterForm,
)
from apps.specialists.models import SpecialistProfile
from apps.users.backends import ActiveStatusModelBackend
from apps.users.models import EmailOTP, User, UserRole, UserStatus

# Сколько карточек показывать на одной странице в каталогах (специалисты,
# вакансии, лента работ) — единое число, чтобы пагинация выглядела одинаково.
PAGE_SIZE = 12


def notify(user, ntype, title, text='', link=''):
    """Создаёт уведомление пользователю внутри сайта.

    Вызывается при событиях, которые должны попасть в колокольчик
    «Уведомления»: новый отклик, принятое предложение, смена статуса сделки,
    новый отзыв. Отправкой почты это не занимается — только записью в базу.
    """
    Notification.objects.create(user=user, type=ntype, title=title, text=text, link=link)


def admin_required(view_func):
    """Декоратор: открывает страницу только администратору площадки.

    Сначала требует авторизации (редирект на страницу входа), затем проверяет
    роль — пользователю без роли ADMIN показывается сообщение об ошибке и
    редирект на главную, а не 403, чтобы не раскрывать структуру панели.
    """
    @wraps(view_func)
    @login_required(login_url='site:login')
    def wrapper(request, *args, **kwargs):
        if request.user.role != UserRole.ADMIN:
            messages.error(request, 'Доступ только для администраторов')
            return redirect('site:home')
        return view_func(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Главная страница
# ---------------------------------------------------------------------------

def home(request):
    """Главная: витрина лучших специалистов, свежих вакансий и работ + статистика."""
    top_specialists = SpecialistProfile.objects.select_related('user').order_by('-rating', '-reviews_count')[:6]
    latest_jobs = Job.objects.select_related('company').filter(status=JobStatus.OPEN)[:6]
    latest_works = Portfolio.objects.select_related('specialist__user').order_by('-created_at')[:3]
    stats = {
        'specialists': SpecialistProfile.objects.count(),
        'jobs': Job.objects.filter(status=JobStatus.OPEN).count(),
        'companies': User.objects.filter(role=UserRole.EMPLOYER).count(),
    }
    return render(request, 'site/home.html', {
        'top_specialists': top_specialists,
        'latest_jobs': latest_jobs,
        'latest_works': latest_works,
        'stats': stats,
    })


# ---------------------------------------------------------------------------
# Регистрация, подтверждение email, вход, выход
# ---------------------------------------------------------------------------

def _send_otp(email):
    """Генерирует новый код подтверждения для email и отправляет его письмом.

    В режиме разработки письмо просто печатается в консоль runserver
    (EMAIL_BACKEND=...console.EmailBackend, см. .env.example).
    """
    otp = EmailOTP.generate(email)
    send_mail(
        subject='Код подтверждения — SMM Marketplace',
        message=f'Ваш код подтверждения: {otp.code}\nОн действует {settings.OTP_TTL_MINUTES} минут.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
    return otp


def register_view(request):
    """Шаг 1 регистрации: форма email/пароль/роль, затем отправка OTP-кода.

    Пользователь в базе ещё не создаётся — его данные (включая хеш пароля)
    временно лежат в сессии до подтверждения кода на следующем шаге. Так
    в базе не остаются «недорегистрированные» аккаунты с неподтверждённым email.
    """
    if request.user.is_authenticated:
        return redirect('site:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            request.session['pending_registration'] = {
                'email': form.cleaned_data['email'],
                'name': form.cleaned_data['name'],
                'role': form.cleaned_data['role'],
                'password_hash': make_password(form.cleaned_data['password']),
            }
            _send_otp(form.cleaned_data['email'])
            messages.info(request, 'Мы отправили код подтверждения на вашу почту')
            return redirect('site:register_verify')
    else:
        form = RegisterForm()

    return render(request, 'site/register.html', {'form': form})


def register_verify(request):
    """Шаг 2 регистрации: проверка OTP-кода и создание аккаунта.

    Код можно запросить повторно (кнопка «Отправить снова» — поле ``resend``
    в форме); каждый новый запрос гасит предыдущие неиспользованные коды
    (см. ``EmailOTP.generate``), поэтому старое письмо с кодом работать не будет.
    """
    pending = request.session.get('pending_registration')
    if not pending:
        return redirect('site:register')

    if request.method == 'POST':
        if 'resend' in request.POST:
            _send_otp(pending['email'])
            messages.info(request, 'Новый код отправлен на почту')
            return redirect('site:register_verify')

        form = OTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            otp = EmailOTP.objects.filter(email=pending['email'], code=code).order_by('-created_at').first()
            if not otp or not otp.is_valid():
                form.add_error('code', 'Код неверен или устарел')
            else:
                otp.mark_used()

                user = User(email=pending['email'], name=pending['name'], role=pending['role'])
                user.password = pending['password_hash']   # уже хеширован на шаге 1
                user.save()

                del request.session['pending_registration']
                # backend указываем явно: пароль только что проверен через OTP,
                # а не через authenticate(), поэтому Django не знает, каким
                # бэкендом подтверждён вход.
                login(request, user, backend=ActiveStatusModelBackend.PATH)
                messages.success(request, 'Email подтверждён! Осталось заполнить профиль.')
                return redirect('site:complete_profile')
    else:
        form = OTPForm()

    return render(request, 'site/register_verify.html', {'form': form, 'email': pending['email']})


def login_view(request):
    """Вход по email и паролю.

    ``authenticate`` сам проверяет блокировку через
    ``ActiveStatusModelBackend`` (settings.AUTHENTICATION_BACKENDS), поэтому
    заблокированный пользователь получит ту же ошибку «неверный email или
    пароль», что и при неправильном пароле — не раскрываем причину отказа.
    """
    if request.user.is_authenticated:
        return redirect('site:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                return redirect('site:dashboard')
            form.add_error(None, 'Неверный email или пароль')
    else:
        form = LoginForm()

    return render(request, 'site/login.html', {'form': form})


@login_required(login_url='site:login')
def logout_view(request):
    """Выход из аккаунта и редирект на главную."""
    logout(request)
    messages.info(request, 'Вы вышли из аккаунта')
    return redirect('site:home')


# ---------------------------------------------------------------------------
# Профиль (компания / специалист)
# ---------------------------------------------------------------------------

@login_required(login_url='site:login')
def complete_profile(request):
    """Первое заполнение профиля после регистрации — компании или специалиста.

    Какую форму показать, определяется ролью пользователя; если профиль уже
    заполнен, незачем показывать форму снова — сразу редирект в кабинет.
    """
    user = request.user
    if user.role == UserRole.EMPLOYER:
        if hasattr(user, 'company'):
            return redirect('site:dashboard')
        form_class, template = CompanyForm, 'site/complete_profile_company.html'
    elif user.role == UserRole.SPECIALIST:
        if hasattr(user, 'specialist_profile'):
            return redirect('site:dashboard')
        form_class, template = SpecialistProfileForm, 'site/complete_profile_specialist.html'
    else:
        return redirect('site:dashboard')

    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = user
            profile.save()
            if hasattr(form, 'save_m2m'):
                form.save_m2m()
            messages.success(request, 'Профиль заполнен!')
            return redirect('site:dashboard')
    else:
        form = form_class()

    return render(request, template, {'form': form})


@login_required(login_url='site:login')
def profile_edit(request):
    """Редактирование уже заполненного профиля (компании или специалиста)."""
    user = request.user
    if user.role == UserRole.EMPLOYER:
        if not hasattr(user, 'company'):
            return redirect('site:complete_profile')
        form_class, template, instance = CompanyForm, 'site/complete_profile_company.html', user.company
    elif user.role == UserRole.SPECIALIST:
        if not hasattr(user, 'specialist_profile'):
            return redirect('site:complete_profile')
        form_class, template, instance = (
            SpecialistProfileForm, 'site/complete_profile_specialist.html', user.specialist_profile,
        )
    else:
        return redirect('site:dashboard')

    if request.method == 'POST':
        form = form_class(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлён')
            return redirect('site:dashboard')
    else:
        form = form_class(instance=instance)

    return render(request, template, {'form': form, 'is_edit': True})


@login_required(login_url='site:login')
def dashboard(request):
    """Личный кабинет: разное содержимое для компании, специалиста и админа.

    Если профиль ещё не заполнен — отправляем на его заполнение; у
    администратора своего кабинета нет, для него кабинет — это панель модерации.
    """
    user = request.user

    if user.role == UserRole.EMPLOYER:
        if not hasattr(user, 'company'):
            return redirect('site:complete_profile')
        jobs = Job.objects.filter(company=user.company).prefetch_related('applications')
        return render(request, 'site/dashboard_employer.html', {
            'user': user, 'company': user.company, 'jobs': jobs,
        })

    if user.role == UserRole.SPECIALIST:
        if not hasattr(user, 'specialist_profile'):
            return redirect('site:complete_profile')
        profile = user.specialist_profile
        applications = Application.objects.select_related('job__company').filter(specialist=profile)
        reviews = Review.objects.filter(recipient=user).order_by('-created_at')[:5]
        return render(request, 'site/dashboard_specialist.html', {
            'user': user, 'profile': profile, 'applications': applications, 'reviews': reviews,
        })

    return redirect('site:panel_dashboard')


# ---------------------------------------------------------------------------
# Каталог специалистов
# ---------------------------------------------------------------------------

SPECIALIST_SORT_MAP = {
    'rating': ('-rating', '-reviews_count'),
    'reviews': ('-reviews_count', '-rating'),
    'price_low': ('price_from',),
    'price_high': ('-price_from',),
    'new': ('-created_at',),
}


def specialists_list(request):
    """Публичный каталог специалистов с поиском, фильтрами и сортировкой."""
    form = SpecialistFilterForm(request.GET or None)
    qs = SpecialistProfile.objects.select_related('user').all()

    if form.is_valid():
        q = form.cleaned_data.get('q')
        specialization = form.cleaned_data.get('specialization')
        city = form.cleaned_data.get('city')
        if q:
            qs = qs.filter(Q(user__name__icontains=q) | Q(bio__icontains=q))
        if specialization:
            qs = qs.filter(specialization=specialization)
        if city:
            qs = qs.filter(city__icontains=city)

        sort = form.cleaned_data.get('sort')
        qs = qs.order_by(*SPECIALIST_SORT_MAP.get(sort, ('-rating', '-created_at')))

    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'site/specialists_list.html', {'form': form, 'page': page})


def specialist_detail(request, pk):
    """Публичная карточка специалиста: описание, последние кейсы, отзывы."""
    profile = get_object_or_404(SpecialistProfile.objects.select_related('user'), pk=pk)
    portfolio_items = profile.portfolio_items.all()[:6]
    reviews = Review.objects.filter(recipient=profile.user).select_related('author').order_by('-created_at')[:10]

    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(
            user=request.user, object_type=FavoriteType.SPECIALIST, object_id=profile.pk,
        ).exists()

    return render(request, 'site/specialist_detail.html', {
        'profile': profile,
        'portfolio_items': portfolio_items,
        'reviews': reviews,
        'is_favorited': is_favorited,
    })


# ---------------------------------------------------------------------------
# Каталог вакансий и отклики
# ---------------------------------------------------------------------------

JOB_SORT_MAP = {
    'new': ('-created_at',),
    'budget_high': ('-budget_from',),
    'budget_low': ('budget_from',),
    'deadline': ('deadline',),
}


def jobs_list(request):
    """Публичный каталог открытых вакансий с поиском, фильтрами и сортировкой."""
    form = JobFilterForm(request.GET or None)
    qs = Job.objects.select_related('company').filter(status=JobStatus.OPEN)

    if form.is_valid():
        q = form.cleaned_data.get('q')
        category = form.cleaned_data.get('category')
        city = form.cleaned_data.get('city')
        if q:
            qs = qs.filter(title__icontains=q)
        if category:
            qs = qs.filter(category=category)
        if city:
            qs = qs.filter(city__icontains=city)

        sort = form.cleaned_data.get('sort')
        qs = qs.order_by(*JOB_SORT_MAP.get(sort, ('-created_at',)))

    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'site/jobs_list.html', {'form': form, 'page': page})


def job_detail(request, pk):
    """Карточка вакансии: кнопка «Откликнуться» для специалиста, список
    откликов — для компании-владельца."""
    job = get_object_or_404(Job.objects.select_related('company'), pk=pk)
    user = request.user

    my_application = None
    can_apply = False
    if user.is_authenticated and user.role == UserRole.SPECIALIST and hasattr(user, 'specialist_profile'):
        my_application = Application.objects.filter(job=job, specialist=user.specialist_profile).first()
        can_apply = my_application is None and job.status == JobStatus.OPEN

    is_owner = user.is_authenticated and hasattr(user, 'company') and job.company_id == user.company.id
    applications = job.applications.select_related('specialist__user') if is_owner else None

    is_favorited = False
    if user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=user, object_type=FavoriteType.JOB, object_id=job.pk).exists()

    return render(request, 'site/job_detail.html', {
        'job': job,
        'my_application': my_application,
        'can_apply': can_apply,
        'is_owner': is_owner,
        'applications': applications,
        'is_favorited': is_favorited,
    })


@login_required(login_url='site:login')
def job_create(request):
    """Публикация новой вакансии — доступно компании с заполненным профилем."""
    user = request.user
    if user.role != UserRole.EMPLOYER or not hasattr(user, 'company'):
        messages.error(request, 'Только компания с заполненным профилем может опубликовать вакансию')
        return redirect('site:dashboard')

    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.company = user.company
            job.save()
            messages.success(request, 'Вакансия опубликована')
            return redirect('site:job_detail', pk=job.pk)
    else:
        form = JobForm()

    return render(request, 'site/job_form.html', {'form': form})


@login_required(login_url='site:login')
def job_apply(request, pk):
    """Отклик специалиста на вакансию: сопроводительное письмо, цена, срок."""
    job = get_object_or_404(Job, pk=pk)
    user = request.user
    if user.role != UserRole.SPECIALIST or not hasattr(user, 'specialist_profile'):
        messages.error(request, 'Откликаться могут только специалисты с заполненным профилем')
        return redirect('site:job_detail', pk=pk)

    if Application.objects.filter(job=job, specialist=user.specialist_profile).exists():
        messages.info(request, 'Вы уже откликнулись на эту вакансию')
        return redirect('site:job_detail', pk=pk)

    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.specialist = user.specialist_profile
            application.save()
            notify(
                job.company.user, NotificationType.APPLICATION, 'Новый отклик',
                f'{user.name} откликнулся на вакансию «{job.title}»',
                reverse('site:job_detail', args=[job.pk]),
            )
            messages.success(request, 'Отклик отправлен')
            return redirect('site:job_detail', pk=pk)
    else:
        form = ApplicationForm()

    return render(request, 'site/job_apply.html', {'form': form, 'job': job})


@login_required(login_url='site:login')
def application_decision(request, pk, decision):
    """Компания принимает или отклоняет отклик специалиста.

    Принятие делает ровно то же, что и в API (apps.jobs.services.accept_application):
    создаёт сделку и переводит вакансию в статус «В работе» — правило живёт
    в одном месте, а не дублируется между сайтом и API.
    """
    application = get_object_or_404(Application.objects.select_related('job__company'), pk=pk)
    user = request.user
    if not hasattr(user, 'company') or application.job.company_id != user.company.id:
        messages.error(request, 'Недостаточно прав')
        return redirect('site:dashboard')

    if request.method == 'POST' and decision in ('accept', 'reject'):
        if decision == 'accept':
            order, _created = accept_application(application)
            notify(
                application.specialist.user, NotificationType.APPLICATION, 'Отклик принят',
                f'Ваш отклик на «{application.job.title}» принят — открыта сделка',
                reverse('site:deal_detail', args=[order.pk]),
            )
        else:
            reject_application(application)
            notify(
                application.specialist.user, NotificationType.APPLICATION, 'Отклик отклонён',
                f'Ваш отклик на «{application.job.title}» отклонён',
                reverse('site:job_detail', args=[application.job_id]),
            )

        messages.success(request, 'Статус отклика обновлён')

    return redirect('site:job_detail', pk=application.job_id)


# ---------------------------------------------------------------------------
# Сообщения (чат)
# ---------------------------------------------------------------------------

def _chat_rows(user):
    """Собирает строки для списка чатов: собеседник, последнее сообщение, непрочитанные.

    Общая подготовка данных для ``chat_list`` и ``chat_detail`` (в последнем
    список чатов показывается сайдбаром).
    """
    rows = []
    for chat in user.chats.prefetch_related('participants').order_by('-created_at'):
        other = chat.participants.exclude(pk=user.pk).first()
        last_message = chat.messages.order_by('-created_at').first()
        unread = chat.messages.filter(read_at__isnull=True).exclude(sender=user).count()
        rows.append({'chat': chat, 'other': other, 'last_message': last_message, 'unread': unread})
    return rows


@login_required(login_url='site:login')
def chat_list(request):
    """Список всех чатов текущего пользователя."""
    return render(request, 'site/chat_list.html', {'rows': _chat_rows(request.user)})


@login_required(login_url='site:login')
def chat_start(request, user_id):
    """Открывает (или создаёт) личный чат с другим пользователем и переходит в него.

    Используется по кнопке «Написать» на карточке специалиста/компании.
    """
    other = get_object_or_404(User, pk=user_id)
    if other.pk == request.user.pk:
        return redirect('site:chat_list')

    chat = get_or_create_direct_chat(request.user, other)
    return redirect('site:chat_detail', pk=chat.pk)


@login_required(login_url='site:login')
def chat_detail(request, pk):
    """Переписка внутри одного чата: отправка сообщений и отметка «прочитано».

    GET открывает чат и сразу отмечает входящие сообщения прочитанными —
    так же, как если бы пользователь физически их увидел.
    """
    chat = get_object_or_404(Chat.objects.prefetch_related('participants'), pk=pk, participants=request.user)
    other = chat.participants.exclude(pk=request.user.pk).first()

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            chat.messages.create(sender=request.user, text=text)
        return redirect('site:chat_detail', pk=chat.pk)

    mark_messages_read(chat, request.user)
    chat_messages = chat.messages.select_related('sender').order_by('created_at')

    return render(request, 'site/chat_detail.html', {
        'chat': chat,
        'other': other,
        'chat_messages': chat_messages,
        'rows': _chat_rows(request.user),
    })


@login_required(login_url='site:login')
def chat_poll(request, pk):
    """Опрос новых сообщений чата по таймеру с фронтенда (без WebSocket).

    Параметр ``after`` — id последнего уже показанного сообщения; отдаются
    только более новые. Используется шаблоном chat_detail.html, который
    дёргает этот адрес раз в несколько секунд через JS.
    """
    chat = get_object_or_404(Chat, pk=pk, participants=request.user)
    after = request.GET.get('after')

    qs = chat.messages.select_related('sender').order_by('created_at')
    if after and after.isdigit():
        qs = qs.filter(pk__gt=int(after))
    new_messages = list(qs)

    mark_messages_read(chat, request.user)

    data = [{
        'id': m.pk,
        'sender_name': m.sender.name,
        'text': m.text,
        'mine': m.sender_id == request.user.id,
        'created_at': m.created_at.strftime('%H:%M'),
    } for m in new_messages]

    return JsonResponse({'messages': data})


# ---------------------------------------------------------------------------
# Портфолио (управление своими кейсами, доступно только специалисту)
# ---------------------------------------------------------------------------

@login_required(login_url='site:login')
def portfolio_manage_list(request):
    """Список собственных кейсов специалиста для редактирования."""
    user = request.user
    if not hasattr(user, 'specialist_profile'):
        messages.error(request, 'Доступно только специалистам с заполненным профилем')
        return redirect('site:dashboard')
    items = Portfolio.objects.filter(specialist=user.specialist_profile).order_by('-created_at')
    return render(request, 'site/portfolio_manage_list.html', {'items': items})


@login_required(login_url='site:login')
def portfolio_create(request):
    """Добавление нового кейса в портфолио."""
    user = request.user
    if not hasattr(user, 'specialist_profile'):
        messages.error(request, 'Доступно только специалистам с заполненным профилем')
        return redirect('site:dashboard')

    if request.method == 'POST':
        form = PortfolioForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.specialist = user.specialist_profile
            item.save()
            messages.success(request, 'Кейс добавлен в портфолио')
            return redirect('site:portfolio_manage_list')
    else:
        form = PortfolioForm()

    return render(request, 'site/portfolio_form.html', {'form': form})


@login_required(login_url='site:login')
def portfolio_edit(request, pk):
    """Редактирование своего кейса портфолио."""
    user = request.user
    item = get_object_or_404(Portfolio, pk=pk)
    if not hasattr(user, 'specialist_profile') or item.specialist_id != user.specialist_profile.id:
        messages.error(request, 'Недостаточно прав')
        return redirect('site:portfolio_manage_list')

    if request.method == 'POST':
        form = PortfolioForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Кейс обновлён')
            return redirect('site:portfolio_manage_list')
    else:
        form = PortfolioForm(instance=item)

    return render(request, 'site/portfolio_form.html', {'form': form, 'item': item})


@login_required(login_url='site:login')
def portfolio_delete(request, pk):
    """Удаление своего кейса портфолио (только POST, только владелец)."""
    user = request.user
    item = get_object_or_404(Portfolio, pk=pk)
    if request.method == 'POST' and hasattr(user, 'specialist_profile') and item.specialist_id == user.specialist_profile.id:
        item.delete()
        messages.info(request, 'Кейс удалён')
    return redirect('site:portfolio_manage_list')


# ---------------------------------------------------------------------------
# Лента работ ("Работы") — публичный просмотр опубликованных кейсов
# ---------------------------------------------------------------------------

WORK_SORT_MAP = {
    'popular': ('-likes_count', '-created_at'),
    'viewed': ('-views_count', '-created_at'),
}


def works_feed(request):
    """Публичная лента всех кейсов портфолио с фильтром по категории и сортировкой."""
    form = WorksFilterForm(request.GET or None)
    qs = Portfolio.objects.select_related('specialist__user')

    sort = 'new'
    if form.is_valid():
        category = form.cleaned_data.get('category')
        sort = form.cleaned_data.get('sort') or 'new'
        if category:
            qs = qs.filter(category=category)

    qs = qs.order_by(*WORK_SORT_MAP.get(sort, ('-created_at',)))

    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))

    # Какие из показанных на странице кейсов лайкнул текущий пользователь —
    # одним запросом для всей страницы, а не по одному на карточку.
    liked_ids = set()
    if request.user.is_authenticated:
        liked_ids = set(
            PortfolioLike.objects.filter(user=request.user, portfolio__in=page.object_list)
            .values_list('portfolio_id', flat=True)
        )

    return render(request, 'site/works_feed.html', {'form': form, 'page': page, 'liked_ids': liked_ids})


def work_detail(request, pk):
    """Карточка кейса в публичной ленте: увеличивает счётчик просмотров."""
    item = get_object_or_404(Portfolio.objects.select_related('specialist__user'), pk=pk)
    register_portfolio_view(item)

    is_liked = False
    if request.user.is_authenticated:
        is_liked = PortfolioLike.objects.filter(portfolio=item, user=request.user).exists()

    return render(request, 'site/work_detail.html', {
        'item': item,
        'media': item.media.all(),
        'is_liked': is_liked,
    })


@login_required(login_url='site:login')
def work_like_toggle(request, pk):
    """Поставить/снять лайк на кейсе и вернуться туда, откуда пришёл запрос."""
    item = get_object_or_404(Portfolio, pk=pk)

    if request.method == 'POST':
        toggle_like(item, request.user)

    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('site:work_detail', pk=pk)


# ---------------------------------------------------------------------------
# Избранное
# ---------------------------------------------------------------------------

@login_required(login_url='site:login')
def favorites_list(request):
    """Список избранного пользователя: специалисты и вакансии.

    Избранное хранится парой «тип + id» без внешнего ключа (см.
    apps/common/models.py), поэтому объекты подгружаются отдельным запросом
    по собранным id каждого типа.
    """
    favorites = Favorite.objects.filter(user=request.user).order_by('-created_at')
    specialist_ids = [f.object_id for f in favorites if f.object_type == FavoriteType.SPECIALIST]
    job_ids = [f.object_id for f in favorites if f.object_type == FavoriteType.JOB]
    specialists = SpecialistProfile.objects.select_related('user').filter(pk__in=specialist_ids)
    jobs = Job.objects.select_related('company').filter(pk__in=job_ids)
    return render(request, 'site/favorites_list.html', {'specialists': specialists, 'jobs': jobs})


@login_required(login_url='site:login')
def favorite_toggle(request, object_type, object_id):
    """Добавляет объект в избранное или убирает его оттуда (переключатель)."""
    if object_type not in FavoriteType.values:
        raise Http404

    if request.method == 'POST':
        obj, created = Favorite.objects.get_or_create(user=request.user, object_type=object_type, object_id=object_id)
        if not created:
            obj.delete()
            messages.info(request, 'Удалено из избранного')
        else:
            messages.success(request, 'Добавлено в избранное')

    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('site:home')


# ---------------------------------------------------------------------------
# Уведомления
# ---------------------------------------------------------------------------

@login_required(login_url='site:login')
def alerts_list(request):
    """Список уведомлений пользователя; при открытии все отмечаются прочитанными."""
    notifications = list(Notification.objects.filter(user=request.user).order_by('-created_at')[:50])
    unread_ids = {n.pk for n in notifications if not n.is_read}
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'site/alerts_list.html', {'notifications': notifications, 'unread_ids': unread_ids})


# ---------------------------------------------------------------------------
# Сделки (заказы) и отзывы
# ---------------------------------------------------------------------------

@login_required(login_url='site:login')
def deals_list(request):
    """Список сделок текущего пользователя — как заказчика или как специалиста."""
    user = request.user
    if hasattr(user, 'company'):
        orders = Order.objects.select_related('specialist__user', 'job').filter(company=user.company)
    elif hasattr(user, 'specialist_profile'):
        orders = Order.objects.select_related('company', 'job').filter(specialist=user.specialist_profile)
    else:
        orders = Order.objects.none()
    return render(request, 'site/deals_list.html', {'orders': orders.order_by('-created_at')})


def _deal_roles(user, order):
    """Определяет, кем в данной сделке выступает пользователь: заказчиком, специалистом или никем."""
    is_company = hasattr(user, 'company') and order.company_id == user.company.id
    is_specialist = hasattr(user, 'specialist_profile') and order.specialist_id == user.specialist_profile.id
    return is_company, is_specialist


@login_required(login_url='site:login')
def deal_detail(request, pk):
    """Карточка сделки: статус, история, кнопка «Оставить отзыв», если применимо."""
    order = get_object_or_404(Order.objects.select_related('company__user', 'specialist__user', 'job'), pk=pk)
    user = request.user
    is_company, is_specialist = _deal_roles(user, order)
    if not (is_company or is_specialist or user.role == UserRole.ADMIN):
        messages.error(request, 'Недостаточно прав')
        return redirect('site:deals_list')

    review = getattr(order, 'review', None)
    can_review = order.status == OrderStatus.COMPLETED and review is None and (is_company or is_specialist)

    return render(request, 'site/deal_detail.html', {
        'order': order, 'is_company': is_company, 'is_specialist': is_specialist,
        'review': review, 'can_review': can_review,
    })


# Переход сделки -> (функция сервиса, кто имеет право его выполнить).
# Права передаются при вызове как уже посчитанные булевы флаги is_company/is_specialist.
_DEAL_TRANSITIONS = {
    'accept': (accept_order, 'is_specialist'),
    'start': (start_order, 'is_specialist'),
    'submit': (submit_order, 'is_specialist'),
    'complete': (complete_order, 'is_company'),
    'cancel': (cancel_order, 'is_company_or_specialist'),
}


@login_required(login_url='site:login')
def deal_transition(request, pk, action):
    """Выполняет действие над сделкой (принять/начать/сдать/завершить/отменить).

    Допустимость самого перехода статуса (например, нельзя «завершить» ещё не
    принятую сделку) проверяет apps.orders.services — здесь проверяются
    только права: кто может нажать эту кнопку.
    """
    order = get_object_or_404(Order.objects.select_related('company__user', 'specialist__user', 'job'), pk=pk)
    user = request.user
    is_company, is_specialist = _deal_roles(user, order)

    transition = _DEAL_TRANSITIONS.get(action)
    if request.method != 'POST' or transition is None:
        return redirect('site:deal_detail', pk=order.pk)

    service_fn, who = transition
    permitted = {
        'is_company': is_company,
        'is_specialist': is_specialist,
        'is_company_or_specialist': is_company or is_specialist,
    }[who]

    if not permitted:
        messages.error(request, 'Недостаточно прав для этого действия')
        return redirect('site:deal_detail', pk=order.pk)

    try:
        service_fn(order)
    except ValidationError:
        # Сервисный слой (apps.orders.services) запретил переход из текущего статуса.
        messages.error(request, f'Нельзя выполнить это действие при текущем статусе «{order.get_status_display()}»')
        return redirect('site:deal_detail', pk=order.pk)

    order.refresh_from_db()
    other_user = order.company.user if is_specialist else order.specialist.user
    notify(
        other_user, NotificationType.ORDER_STATUS, 'Статус сделки изменён',
        f'Сделка №{order.pk}: {order.get_status_display()}',
        reverse('site:deal_detail', args=[order.pk]),
    )
    messages.success(request, 'Статус обновлён')
    return redirect('site:deal_detail', pk=order.pk)


@login_required(login_url='site:login')
def deal_review(request, pk):
    """Отзыв по завершённой сделке: доступен обеим сторонам, но только один раз на сделку."""
    order = get_object_or_404(Order.objects.select_related('company__user', 'specialist__user'), pk=pk)
    user = request.user
    is_company, is_specialist = _deal_roles(user, order)

    if not (is_company or is_specialist):
        messages.error(request, 'Недостаточно прав')
        return redirect('site:deals_list')
    if order.status != OrderStatus.COMPLETED:
        messages.error(request, 'Отзыв можно оставить только после завершения сделки')
        return redirect('site:deal_detail', pk=pk)
    if hasattr(order, 'review'):
        messages.info(request, 'Отзыв уже оставлен')
        return redirect('site:deal_detail', pk=pk)

    recipient = order.specialist.user if is_company else order.company.user

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.order = order
            review.author = user
            review.recipient = recipient
            review.save()
            # Рейтинг специалиста пересчитывается, только если отзыв получил именно он.
            if recipient.pk == order.specialist.user_id:
                refresh_specialist_rating(order.specialist)
            notify(
                recipient, NotificationType.REVIEW, 'Новый отзыв',
                f'Вы получили отзыв по сделке №{order.pk}',
                reverse('site:deal_detail', args=[order.pk]),
            )
            messages.success(request, 'Отзыв сохранён')
            return redirect('site:deal_detail', pk=pk)
    else:
        form = ReviewForm()

    return render(request, 'site/review_form.html', {'form': form, 'order': order})


# ---------------------------------------------------------------------------
# Жалобы (модерационные обращения пользователей)
# ---------------------------------------------------------------------------

@login_required(login_url='site:login')
def report_create(request, target_type, target_id):
    """Форма жалобы на объект площадки (профиль, вакансию, отзыв и т. д.)."""
    if target_type not in ComplaintTargetType.values:
        raise Http404

    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.reporter = request.user
            complaint.target_type = target_type
            complaint.target_id = target_id
            complaint.save()
            messages.success(request, 'Жалоба отправлена на рассмотрение')
            next_url = request.POST.get('next', '')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('site:home')
    else:
        form = ComplaintForm()

    return render(request, 'site/report_form.html', {'form': form, 'target_type': target_type, 'target_id': target_id})


# ---------------------------------------------------------------------------
# Панель администратора (встроена в сайт, отдельная от /admin/ Django)
# ---------------------------------------------------------------------------

@admin_required
def panel_dashboard(request):
    """Сводная статистика площадки для модератора."""
    stats = {
        'users': User.objects.count(),
        'specialists': SpecialistProfile.objects.count(),
        'companies': Company.objects.count(),
        'jobs_open': Job.objects.filter(status=JobStatus.OPEN).count(),
        'orders': Order.objects.count(),
        'complaints_pending': Complaint.objects.filter(status=ComplaintStatus.PENDING).count(),
    }
    return render(request, 'site/panel_dashboard.html', {'stats': stats})


@admin_required
def panel_users(request):
    """Список пользователей для модерации (последние 200)."""
    users = User.objects.order_by('-created_at')[:200]
    return render(request, 'site/panel_users.html', {'users': users})


@admin_required
def panel_user_toggle_block(request, pk):
    """Блокирует/разблокирует пользователя. Себя заблокировать нельзя — иначе
    администратор мог бы случайно потерять доступ к панели."""
    target = get_object_or_404(User, pk=pk)
    if request.method == 'POST' and target.pk != request.user.pk:
        target.status = UserStatus.BLOCKED if target.status == UserStatus.ACTIVE else UserStatus.ACTIVE
        target.save(update_fields=['status'])
        messages.success(request, f'Статус пользователя обновлён: {target.get_status_display()}')
    return redirect('site:panel_users')


@admin_required
def panel_complaints(request):
    """Список жалоб для разбора модератором (последние 200)."""
    complaints = Complaint.objects.select_related('reporter').order_by('-created_at')[:200]
    return render(request, 'site/panel_complaints.html', {'complaints': complaints})


@admin_required
def panel_complaint_decision(request, pk, decision):
    """Решение модератора по жалобе: признать обоснованной или отклонить."""
    complaint = get_object_or_404(Complaint, pk=pk)
    if request.method == 'POST' and decision in ('resolve', 'reject'):
        complaint.status = ComplaintStatus.RESOLVED if decision == 'resolve' else ComplaintStatus.REJECTED
        complaint.resolved_by = request.user
        complaint.resolved_at = timezone.now()
        complaint.save(update_fields=['status', 'resolved_by', 'resolved_at'])
        messages.success(request, 'Жалоба обработана')
    return redirect('site:panel_complaints')


@admin_required
def panel_jobs(request):
    """Список вакансий для модерации (последние 200)."""
    jobs = Job.objects.select_related('company').order_by('-created_at')[:200]
    return render(request, 'site/panel_jobs.html', {'jobs': jobs})


@admin_required
def panel_job_moderate(request, pk, decision):
    """Закрывает или отменяет вакансию по решению модератора."""
    job = get_object_or_404(Job, pk=pk)
    if request.method == 'POST' and decision in ('close', 'cancel'):
        job.status = JobStatus.CLOSED if decision == 'close' else JobStatus.CANCELLED
        job.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Вакансия обновлена')
    return redirect('site:panel_jobs')
