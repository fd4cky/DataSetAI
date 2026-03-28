# DataSetAI

DataSetAI - Django-сервис для командной разметки датасетов. Проект сочетает серверный UI, REST API, PostgreSQL, CI на Pull Request и автодеплой в production после merge в `main`.

## Что умеет проект

- регистрация и вход пользователей
- создание комнат для разметки
- приглашение аннотаторов в комнаты
- работа с текстовыми, image- и video-задачами
- сохранение аннотаций и назначений по задачам
- локальный запуск через `.env`
- CI на GitHub Actions
- автодеплой на production-сервер

## Технологический стек

- Backend: Django 5
- API: Django REST Framework
- Frontend: Django Templates + Vanilla JavaScript + CSS
- Database: PostgreSQL 14+
- DB driver: `psycopg`
- Config: `.env` + `python-dotenv`
- Production app server: `gunicorn`
- Reverse proxy: `nginx`
- Service manager: `systemd`
- CI/CD: GitHub Actions

Подробное описание архитектуры лежит в [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Карта документации

- Локальная разработка и быстрый старт: этот файл
- Архитектура и устройство приложения: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Production, CI/CD и эксплуатация сервера: [DEPLOY.md](DEPLOY.md)

## Быстрый старт локально

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd DataSetAI
```

### 2. Создать виртуальное окружение

```bash
python -m venv .venv
```

### 3. Активировать окружение

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### 4. Установить зависимости

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements/local.txt
```

### 5. Создать `.env`

```bash
# macOS / Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Пример локального `.env`:

```env
DJANGO_SECRET_KEY=unsafe-local-secret-key
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
TIME_ZONE=UTC

DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=127.0.0.1
DB_PORT=6543
```

Все `DB_*` значения обязательны. Если `.env` отсутствует или в нём не заполнены обязательные переменные, Django завершится с понятной ошибкой на старте.

### 6. Поднять доступ к БД

Если вы используете удалённую dev-базу, поднимите SSH-туннель в отдельном терминале:

```powershell
ssh -N -L 6543:127.0.0.1:5432 <ssh_user>@<server_ip>
```

Если у вас локальный PostgreSQL, просто укажите в `.env` его реальные `DB_*` параметры.

### 7. Проверить соединение с БД

```bash
python scripts/check_db.py
```

### 8. Применить миграции

```bash
python manage.py migrate
```

### 9. При необходимости создать тестовые данные

```bash
python manage.py seed_mvp_data
```

### 10. Запустить проект

```bash
python manage.py runserver
```

После этого приложение доступно на `http://127.0.0.1:8000/`.

## Полезные команды для локальной разработки

```bash
python scripts/check_db.py
python manage.py check
python manage.py test
python manage.py migrate
python manage.py seed_mvp_data
python manage.py create_local_user alice strongpass123 --email alice@example.com
python manage.py runserver
```

## Быстрый bootstrap

Если у вас есть Bash, можно ускорить первый запуск:

```bash
bash bin/bootstrap_local.sh
```

Скрипт:

- создаёт `.venv`, если его ещё нет
- ставит зависимости
- создаёт `.env` из `.env.example`, если файла ещё нет

После этого всё равно нужно заполнить `.env` и настроить доступ к БД.

## Как работает команда

Обычный цикл:

1. Обновить `main`
2. Создать ветку от `main`
3. Внести изменения локально
4. Проверить проект локально
5. Запушить ветку на GitHub
6. Открыть Pull Request в `main`
7. Дождаться зелёного CI
8. Смерджить PR
9. Дождаться production deploy

На Pull Request автоматически запускается CI:

- `python manage.py check`
- `python manage.py test`

После merge в `main` GitHub Actions автоматически выполняет production deploy.

## Структура репозитория

- `apps/` - доменные Django-приложения
- `config/` - settings, URL routing, ASGI/WSGI
- `common/` - общая инфраструктура и middleware
- `scripts/` - служебные Python-скрипты
- `bin/` - bootstrap-скрипты
- `tests/` - тесты
- `.github/workflows/` - CI и production deploy

## Замечания по image/video задачам

- локально media-файлы обслуживаются Django только при `DEBUG=true`
- в production media обслуживает `nginx`
- для корректной работы image/video upload на сервере должны быть настроены:
  - каталог `media/`
  - `location /media/` в `nginx`
  - достаточный `client_max_body_size`

Эти детали описаны в [DEPLOY.md](DEPLOY.md).
