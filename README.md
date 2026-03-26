# DataSetAI Backend MVP

Минимальная первая итерация backend-сервиса для платформы краудсорсинговой разметки датасетов.

## Что есть сейчас

- Django + Django REST Framework
- PostgreSQL как обязательная локальная БД
- Встроенный UI для ручной проверки
- Комнаты, участники, задачи, аннотации
- Простая регистрация и логин
- API `v1`
- Seed-данные для локальной проверки
- Базовые тесты ключевых сценариев

Важно: глобальной роли пользователя больше нет. Любой пользователь может:

- создать комнату и в этой комнате выступать заказчиком
- войти в чужую комнату и там выступать исполнителем

## Быстрый старт после clone

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd DataSetAI
```

### 2. Поднять окружение

Самый простой вариант:

```bash
bash bin/bootstrap_local.sh
```

Что делает скрипт:

- создает `.venv`, если его еще нет
- ставит зависимости
- создает `.env` из `.env.example`, если файла еще нет

### 3. Настроить PostgreSQL

Проект теперь понимает оба набора переменных:

- предпочтительно: `DB_*`
- legacy-совместимость: `POSTGRES_*`

Пример `.env`:

```env
DJANGO_SECRET_KEY=unsafe-local-secret-key
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
TIME_ZONE=UTC

DB_HOST=127.0.0.1
DB_PORT=6543
DB_NAME=dataset_ai_db
DB_USER=dataset_ai_app
DB_PASSWORD=твой_пароль
```

Если удобнее, можно использовать старые переменные:

```env
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=datasetai
POSTGRES_USER=w
POSTGRES_PASSWORD=
```

### 4. Создать пользователя и базу в PostgreSQL

Если у тебя уже есть PostgreSQL и доступ под админом:

```sql
CREATE USER dataset_ai_app WITH PASSWORD 'твой_пароль';
CREATE DATABASE dataset_ai_db OWNER dataset_ai_app;
```

Если база и пользователь уже выданы инфраструктурой, этот шаг пропускаешь и просто заполняешь `.env`.

### 5. Применить миграции и seed

```bash
source .venv/bin/activate
python3 manage.py migrate
python3 manage.py seed_mvp_data
```

### 6. Запустить проект

```bash
python3 manage.py runserver
```

Доступные страницы:

- `/`
- `/rooms/`
- `/profile/`
- `/auth/login/`
- `/auth/register/`
- `/health/`
- `/api/v1/`

## Как добавлять новых людей

Есть 3 нормальных способа.

### Вариант 1. Через UI

Для обычных пользователей:

1. открыть `/auth/register/`
2. ввести логин и пароль
3. после входа пользователь уже может создавать комнаты и входить в чужие

### Вариант 2. Через management command

Для локальной разработки удобнее так:

```bash
python3 manage.py create_local_user alice strongpass123 --email alice@example.com
```

Если нужен доступ в Django admin:

```bash
python3 manage.py create_local_user lead strongpass123 --email lead@example.com --staff
```

Если нужен полноценный superuser:

```bash
python3 manage.py create_local_user root strongpass123 --email root@example.com --superuser
```

Команда создаст пользователя, а если он уже есть, обновит пароль и флаги доступа.

### Вариант 3. Через Django admin

Если у тебя уже есть staff/superuser:

1. открыть `/admin/`
2. создать пользователя вручную

## Тестовые пользователи

После `python3 manage.py seed_mvp_data` будут доступны:

- `admin / admin`
- `user / user`

Также seed создаст:

- demo room
- тестовые задачи
- несколько приглашенных пользователей

## Как сделать запуск у новых разработчиков без боли

Ниже практичные правила, которые уже частично внедрены в проект.

### Что уже сделано

- `.env` читается автоматически
- поддерживаются `DB_*` и `POSTGRES_*`
- есть `.env.example`
- есть `bin/bootstrap_local.sh`
- есть `seed_mvp_data`
- есть `create_local_user`

### Что должен сделать новый разработчик

Минимальный путь:

```bash
git clone <repo-url>
cd DataSetAI
bash bin/bootstrap_local.sh
cp .env.example .env  # если bootstrap еще не создавал
python3 manage.py migrate
python3 manage.py seed_mvp_data
python3 manage.py runserver
```

Если PostgreSQL не поднят или нет базы, сначала нужно:

1. получить доступы
2. создать базу и пользователя
3. заполнить `.env`

### Что важно не ломать дальше

- не хардкодить параметры БД в settings
- не завязывать локальный запуск на одного системного пользователя
- не хранить реальные пароли в репозитории
- держать `.env.example` в актуальном состоянии
- при добавлении новых обязательных env-переменных сразу отражать их в README

## Архитектура

- `config/` — settings, root urls, ASGI/WSGI
- `apps/*/models.py` — доменные модели
- `apps/*/services.py` — бизнес-логика
- `apps/*/selectors.py` — read-queries
- `apps/*/api/v1/` — текущий transport layer
- `common/` — общая инфраструктура

Такой расклад позволяет позже:

- заменить текущую auth-модель без переписывания сервисов
- менять shape API без массового рефакторинга
- развернуть систему и локально, и на клиентском сервере

## Основные команды

```bash
python3 manage.py migrate
python3 manage.py seed_mvp_data
python3 manage.py create_local_user alice strongpass123 --email alice@example.com
python3 manage.py runserver
python3 manage.py test
```
