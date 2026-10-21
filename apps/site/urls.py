"""
Маршруты веб-интерфейса (HTML-страницы на Django-шаблонах).

Сгруппированы по разделам в том же порядке, в каком идут комментарии-заголовки
в apps/site/views.py, — так проще сопоставлять адрес с его обработчиком.
"""

from django.urls import path

from apps.site import views

app_name = 'site'   # пространство имён для {% url 'site:...' %} в шаблонах

urlpatterns = [
    path('', views.home, name='home'),

    # --- Регистрация, вход, выход ------------------------------------------
    path('register/', views.register_view, name='register'),
    path('register/verify/', views.register_verify, name='register_verify'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # --- Профиль и личный кабинет -------------------------------------------
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # --- Сообщения (чат) -----------------------------------------------------
    path('messages/', views.chat_list, name='chat_list'),
    path('messages/start/<int:user_id>/', views.chat_start, name='chat_start'),
    path('messages/<int:pk>/', views.chat_detail, name='chat_detail'),
    path('messages/<int:pk>/poll/', views.chat_poll, name='chat_poll'),   # опрос новых сообщений по таймеру

    # --- Каталог специалистов ------------------------------------------------
    path('talents/', views.specialists_list, name='specialists_list'),
    path('talents/<int:pk>/', views.specialist_detail, name='specialist_detail'),

    # --- Каталог вакансий и отклики -------------------------------------------
    path('vacancies/', views.jobs_list, name='jobs_list'),
    path('vacancies/new/', views.job_create, name='job_create'),
    path('vacancies/<int:pk>/', views.job_detail, name='job_detail'),
    path('vacancies/<int:pk>/apply/', views.job_apply, name='job_apply'),
    path('vacancies/responses/<int:pk>/<str:decision>/', views.application_decision, name='application_decision'),

    # --- Лента работ (публичное портфолио) ------------------------------------
    path('works/', views.works_feed, name='works_feed'),
    path('works/<int:pk>/', views.work_detail, name='work_detail'),
    path('works/<int:pk>/like/', views.work_like_toggle, name='work_like_toggle'),

    # --- Управление своим портфолио (специалист) --------------------------------
    path('my-portfolio/', views.portfolio_manage_list, name='portfolio_manage_list'),
    path('my-portfolio/new/', views.portfolio_create, name='portfolio_create'),
    path('my-portfolio/<int:pk>/edit/', views.portfolio_edit, name='portfolio_edit'),
    path('my-portfolio/<int:pk>/delete/', views.portfolio_delete, name='portfolio_delete'),

    # --- Избранное -------------------------------------------------------------
    path('saved/', views.favorites_list, name='favorites_list'),
    path('saved/toggle/<str:object_type>/<int:object_id>/', views.favorite_toggle, name='favorite_toggle'),

    # --- Уведомления -------------------------------------------------------------
    path('alerts/', views.alerts_list, name='alerts_list'),

    # --- Сделки и отзывы ----------------------------------------------------------
    path('deals/', views.deals_list, name='deals_list'),
    path('deals/<int:pk>/', views.deal_detail, name='deal_detail'),
    path('deals/<int:pk>/review/', views.deal_review, name='deal_review'),
    path('deals/<int:pk>/<str:action>/', views.deal_transition, name='deal_transition'),

    # --- Жалобы --------------------------------------------------------------------
    path('report/<str:target_type>/<int:target_id>/', views.report_create, name='report_create'),

    # --- Панель администратора (встроена в сайт) -------------------------------------
    path('panel/', views.panel_dashboard, name='panel_dashboard'),
    path('panel/users/', views.panel_users, name='panel_users'),
    path('panel/users/<int:pk>/toggle-block/', views.panel_user_toggle_block, name='panel_user_toggle_block'),
    path('panel/complaints/', views.panel_complaints, name='panel_complaints'),
    path('panel/complaints/<int:pk>/<str:decision>/', views.panel_complaint_decision, name='panel_complaint_decision'),
    path('panel/jobs/', views.panel_jobs, name='panel_jobs'),
    path('panel/jobs/<int:pk>/<str:decision>/', views.panel_job_moderate, name='panel_job_moderate'),
]
