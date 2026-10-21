"""
Django-формы веб-интерфейса.

Это HTML-аналог сериализаторов REST API: валидируют данные из обычных
``<form>`` и отрисовывают поля с едиными CSS-классами (``field``), которые
стилизует apps/site/static/site/css/style.css.
"""

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.common.choices import ComplaintReason, Specialization, WorkFormat
from apps.common.models import Complaint
from apps.companies.models import Company
from apps.jobs.models import Application, Job
from apps.orders.models import Review
from apps.portfolio.models import Portfolio
from apps.specialists.models import SpecialistProfile
from apps.users.models import User, UserRole

# Общие виджеты, чтобы все текстовые поля проекта выглядели одинаково —
# подключается к полям формы через widgets={...} в Meta.
TEXT_WIDGET = forms.TextInput(attrs={'class': 'field'})
TEXTAREA_WIDGET = forms.Textarea(attrs={'class': 'field', 'rows': 4})


class RegisterForm(forms.Form):
    """Шаг 1 регистрации: роль, имя, email, пароль (с подтверждением).

    Пользователь ещё не создаётся при валидации этой формы — создание
    происходит только после подтверждения email-кода (см. ``register_verify``
    в apps/site/views.py).
    """

    role = forms.ChoiceField(
        choices=[(UserRole.EMPLOYER, 'Я ищу специалиста'), (UserRole.SPECIALIST, 'Я специалист')],
        widget=forms.RadioSelect,
        initial=UserRole.EMPLOYER,
    )
    name = forms.CharField(label='Имя', widget=TEXT_WIDGET)
    email = forms.EmailField(label='Email', widget=TEXT_WIDGET)
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': 'field'}))
    password2 = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput(attrs={'class': 'field'}))

    def clean_email(self):
        """Приводит email к нижнему регистру и проверяет, что он свободен."""
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже зарегистрирован')
        return email

    def clean_password(self):
        """Прогоняет пароль через стандартные валидаторы Django (длина, похожесть и т. д.)."""
        password = self.cleaned_data['password']
        validate_password(password)
        return password

    def clean(self):
        """Проверяет, что пароль и его повтор совпадают."""
        cleaned = super().clean()
        if cleaned.get('password') and cleaned.get('password2') and cleaned['password'] != cleaned['password2']:
            self.add_error('password2', 'Пароли не совпадают')
        return cleaned


class LoginForm(forms.Form):
    """Форма входа: email и пароль. Сама проверка пары делается в login_view
    через ``django.contrib.auth.authenticate``, а не здесь."""

    email = forms.EmailField(label='Email', widget=TEXT_WIDGET)
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': 'field'}))


class OTPForm(forms.Form):
    """Форма ввода 6-значного кода подтверждения email, присланного письмом."""

    code = forms.CharField(
        label='Код из письма',
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'field', 'inputmode': 'numeric', 'autocomplete': 'one-time-code',
            'placeholder': '000000', 'style': 'letter-spacing:.4em;text-align:center;font-size:20px;',
        }),
    )

    def clean_code(self):
        """Проверяет, что введённый код состоит только из цифр (сам код сверяется во вьюхе)."""
        code = self.cleaned_data['code']
        if not code.isdigit():
            raise ValidationError('Код должен состоять из 6 цифр')
        return code


class CompanyForm(forms.ModelForm):
    """Заполнение/редактирование профиля компании-заказчика."""

    class Meta:
        model = Company
        fields = ['name', 'industry', 'website', 'country', 'city', 'description']
        widgets = {
            'name': TEXT_WIDGET,
            'industry': TEXT_WIDGET,
            'website': TEXT_WIDGET,
            'country': TEXT_WIDGET,
            'city': TEXT_WIDGET,
            'description': TEXTAREA_WIDGET,
        }


class SpecialistProfileForm(forms.ModelForm):
    """Заполнение/редактирование профиля специалиста.

    Поля репутации (рейтинг, счётчики, статус проверки) в форме отсутствуют —
    их меняет только сервер при отзывах, завершённых сделках и модерации.
    """

    specialization = forms.ChoiceField(choices=Specialization.choices, widget=forms.Select(attrs={'class': 'field'}))
    work_format = forms.ChoiceField(choices=WorkFormat.choices, widget=forms.Select(attrs={'class': 'field'}))

    class Meta:
        model = SpecialistProfile
        fields = [
            'specialization', 'bio', 'experience_years', 'country', 'city',
            'price_from', 'price_to', 'work_format',
        ]
        widgets = {
            'bio': TEXTAREA_WIDGET,
            'experience_years': forms.NumberInput(attrs={'class': 'field', 'min': 0}),
            'country': TEXT_WIDGET,
            'city': TEXT_WIDGET,
            'price_from': forms.NumberInput(attrs={'class': 'field'}),
            'price_to': forms.NumberInput(attrs={'class': 'field'}),
        }


class JobForm(forms.ModelForm):
    """Публикация/редактирование вакансии компанией."""

    category = forms.ChoiceField(choices=Specialization.choices, widget=forms.Select(attrs={'class': 'field'}))
    work_format = forms.ChoiceField(choices=WorkFormat.choices, widget=forms.Select(attrs={'class': 'field'}))

    class Meta:
        model = Job
        fields = [
            'title', 'description', 'category', 'budget_type', 'budget_from', 'budget_to',
            'deadline', 'work_format', 'country', 'city',
        ]
        widgets = {
            'title': TEXT_WIDGET,
            'description': TEXTAREA_WIDGET,
            'budget_type': forms.Select(attrs={'class': 'field'}),
            'budget_from': forms.NumberInput(attrs={'class': 'field'}),
            'budget_to': forms.NumberInput(attrs={'class': 'field'}),
            'deadline': forms.DateInput(attrs={'class': 'field', 'type': 'date'}),
            'country': TEXT_WIDGET,
            'city': TEXT_WIDGET,
        }


class ApplicationForm(forms.ModelForm):
    """Отклик специалиста на вакансию: сопроводительное письмо, цена, срок."""

    class Meta:
        model = Application
        fields = ['message', 'price', 'deadline']
        widgets = {
            'message': TEXTAREA_WIDGET,
            'price': forms.NumberInput(attrs={'class': 'field'}),
            'deadline': forms.DateInput(attrs={'class': 'field', 'type': 'date'}),
        }


# Шкала оценки 1–5, общая для всех пяти критериев отзыва.
RATING_CHOICES = [(n, f'{n} — {label}') for n, label in [
    (5, 'Отлично'), (4, 'Хорошо'), (3, 'Нормально'), (2, 'Плохо'), (1, 'Ужасно'),
]]
RATING_WIDGET = forms.Select(attrs={'class': 'field'}, choices=RATING_CHOICES)


class PortfolioForm(forms.ModelForm):
    """Добавление/редактирование кейса в портфолио специалиста."""

    category = forms.ChoiceField(choices=Specialization.choices, widget=forms.Select(attrs={'class': 'field'}))

    class Meta:
        model = Portfolio
        fields = [
            'title', 'category', 'description', 'client_task', 'work_done', 'result',
            'cover', 'period_from', 'period_to',
        ]
        widgets = {
            'title': TEXT_WIDGET,
            'description': TEXTAREA_WIDGET,
            'client_task': TEXTAREA_WIDGET,
            'work_done': TEXTAREA_WIDGET,
            'result': TEXTAREA_WIDGET,
            'period_from': forms.DateInput(attrs={'class': 'field', 'type': 'date'}),
            'period_to': forms.DateInput(attrs={'class': 'field', 'type': 'date'}),
        }


class ReviewForm(forms.ModelForm):
    """Отзыв по завершённой сделке: общая оценка + четыре частных критерия."""

    class Meta:
        model = Review
        fields = ['rating', 'quality_rating', 'timeliness_rating', 'communication_rating', 'compliance_rating', 'text']
        labels = {
            'rating': 'Общая оценка',
            'quality_rating': 'Качество работы',
            'timeliness_rating': 'Соблюдение сроков',
            'communication_rating': 'Коммуникация',
            'compliance_rating': 'Соответствие ТЗ',
            'text': 'Комментарий',
        }
        widgets = {
            'rating': RATING_WIDGET,
            'quality_rating': RATING_WIDGET,
            'timeliness_rating': RATING_WIDGET,
            'communication_rating': RATING_WIDGET,
            'compliance_rating': RATING_WIDGET,
            'text': TEXTAREA_WIDGET,
        }


class ComplaintForm(forms.ModelForm):
    """Форма жалобы на объект площадки: причина + комментарий.

    Куда именно жалуется пользователь (``target_type``/``target_id``)
    передаётся не через форму, а через URL (см. ``report_create`` в views.py).
    """

    reason = forms.ChoiceField(choices=ComplaintReason.choices, widget=forms.Select(attrs={'class': 'field'}))

    class Meta:
        model = Complaint
        fields = ['reason', 'comment']
        widgets = {'comment': TEXTAREA_WIDGET}


# --- Формы поиска и сортировки каталогов (не привязаны к модели) -------------

SPECIALIST_SORT_CHOICES = [
    ('relevance', 'По релевантности'),
    ('rating', 'По рейтингу'),
    ('reviews', 'По отзывам'),
    ('price_low', 'Сначала дешевле'),
    ('price_high', 'Сначала дороже'),
    ('new', 'Сначала новые'),
]

JOB_SORT_CHOICES = [
    ('relevance', 'По релевантности'),
    ('new', 'Сначала новые'),
    ('budget_high', 'Бюджет: по убыванию'),
    ('budget_low', 'Бюджет: по возрастанию'),
    ('deadline', 'По сроку'),
]

WORK_SORT_CHOICES = [
    ('new', 'Новые'),
    ('popular', 'По лайкам'),
    ('viewed', 'По просмотрам'),
]


class SpecialistFilterForm(forms.Form):
    """Поиск и фильтры каталога специалистов (``apps.site.views.specialists_list``).

    Все поля ``required=False`` — форма валидна и с пустым GET-запросом,
    тогда каталог просто показывается без фильтров.
    """

    q = forms.CharField(required=False, label='Поиск', widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'Имя или навык…'}))
    specialization = forms.ChoiceField(required=False, choices=[('', 'Любая специализация')] + list(Specialization.choices), widget=forms.Select(attrs={'class': 'field'}))
    city = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'Город'}))
    sort = forms.ChoiceField(required=False, choices=SPECIALIST_SORT_CHOICES, widget=forms.Select(attrs={'class': 'field'}))


class JobFilterForm(forms.Form):
    """Поиск и фильтры каталога вакансий (``apps.site.views.jobs_list``)."""

    q = forms.CharField(required=False, label='Поиск', widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'Название…'}))
    category = forms.ChoiceField(required=False, choices=[('', 'Любая категория')] + list(Specialization.choices), widget=forms.Select(attrs={'class': 'field'}))
    city = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'Город'}))
    sort = forms.ChoiceField(required=False, choices=JOB_SORT_CHOICES, widget=forms.Select(attrs={'class': 'field'}))


class WorksFilterForm(forms.Form):
    """Фильтр и сортировка публичной ленты работ (``apps.site.views.works_feed``)."""

    category = forms.ChoiceField(required=False, choices=[('', 'Все категории')] + list(Specialization.choices), widget=forms.Select(attrs={'class': 'field'}))
    sort = forms.ChoiceField(required=False, choices=WORK_SORT_CHOICES, widget=forms.Select(attrs={'class': 'field'}))
