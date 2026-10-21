# Деплой на PythonAnywhere

Логин на PythonAnywhere: `mslm0990`.
Сайт будет доступен по адресу `https://mslm0990.pythonanywhere.com`.

## 1. Регистрация

Зарегистрируйтесь на <https://www.pythonanywhere.com> (тариф **Beginner** — бесплатный).

## 2. Клонирование и окружение

Dashboard → **Consoles** → **Bash**:

```bash
git clone https://github.com/muslimamamatova/SmmBackend.git
cd SmmBackend

mkvirtualenv --python=python3.11 smm
pip install -r requirements.txt
```

> Если консоль закрылась, окружение включается командой `workon smm`.

## 3. Файл .env

```bash
cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
nano .env
```

Поменяйте в `.env` (остальное можно оставить как есть):

```ini
SECRET_KEY=<ключ, который напечатала команда выше>
DEBUG=False
ALLOWED_HOSTS=mslm0990.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://mslm0990.pythonanywhere.com
SECURE_SSL_REDIRECT=True
```

Сохранить в nano: `Ctrl+O`, `Enter`, выйти: `Ctrl+X`.

## 4. База, статика, админ

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
mkdir -p media
```

## 5. Веб-приложение

Вкладка **Web** → **Add a new web app** → **Next** → **Manual configuration**
(не «Django»!) → **Python 3.11** → **Next**.

На странице приложения:

**Virtualenv**

```
/home/mslm0990/.virtualenvs/smm
```

**Code → Source code**

```
/home/mslm0990/SmmBackend
```

**Code → WSGI configuration file** — откройте ссылку, удалите всё содержимое
и вставьте код из [`deploy/pythonanywhere_wsgi.py`](pythonanywhere_wsgi.py),
и нажмите **Save**.

**Static files** — добавьте две строки:

| URL       | Directory                              |
|-----------|----------------------------------------|
| `/static/` | `/home/mslm0990/SmmBackend/staticfiles` |
| `/media/`  | `/home/mslm0990/SmmBackend/media`       |

**Security** → включите **Force HTTPS**.

Нажмите зелёную кнопку **Reload** вверху страницы и откройте сайт.

## 6. Почта (коды подтверждения регистрации)

По умолчанию письма не отправляются, а пишутся в лог (`EMAIL_BACKEND=...console...`).
Их видно во вкладке Web → **Server log**.

На бесплатном тарифе исходящий интернет ограничен белым списком, поэтому
реальную отправку проще всего сделать через Gmail. Создайте пароль приложения
(Google-аккаунт → Безопасность → Двухэтапная аутентификация → Пароли приложений)
и пропишите в `.env`:

```ini
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш@gmail.com
EMAIL_HOST_PASSWORD=<пароль приложения, 16 символов>
DEFAULT_FROM_EMAIL=ваш@gmail.com
```

После изменения `.env` — **Reload**.

## Обновление сайта после нового push

```bash
cd ~/SmmBackend
workon smm
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Затем **Reload** во вкладке Web.

## Если что-то не работает

- **Ошибка на сайте** → Web → **Error log** (внизу страницы), последние строки.
- **DisallowedHost** → проверьте `ALLOWED_HOSTS` в `.env`.
- **CSRF verification failed** → проверьте `CSRF_TRUSTED_ORIGINS` (с `https://`).
- **Нет стилей** → не выполнен `collectstatic` или неверный путь в Static files.
- **Сайт отключили** → бесплатный сайт нужно продлевать раз в 3 месяца кнопкой
  «Run until 3 months from today» во вкладке Web.
