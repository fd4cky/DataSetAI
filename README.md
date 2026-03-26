# DataSetAI Backend MVP

Минимальная первая итерация backend-сервиса для платформы краудсорсинговой разметки датасетов.

## Что реализовано

- Django + Django REST Framework
- PostgreSQL как обязательная БД для локального MVP
- Кастомная модель `User` с ролью `customer` или `annotator`
- Временная идентификация через header `X-User-Id`
- Встроенный браузерный UI для ручной проверки customer/annotator сценариев
- Rooms, memberships, tasks, annotations
- Сервисный слой для бизнес-логики
- API `v1`, который можно переписывать без болезненного рефакторинга доменной логики
- Seed-данные для локальной проверки
- Базовые API-тесты ключевых сценариев

## Архитектурная идея

Проект разделен на несколько слоев:

- `config/` — настройки, корневые `urls`, ASGI/WSGI
- `apps/*/models.py` — доменная модель и схема хранения
- `apps/*/services.py` — бизнес-операции и use-cases
- `apps/*/selectors.py` — read-queries
- `apps/*/api/v1/` — serializers, views, urls текущей версии API
- `common/` — общая инфраструктура: auth, permissions, exceptions

Это позволяет позже:

- заменить `X-User-Id` на реальную auth-систему без переписывания сервисов
- поменять endpoint-ы или ввести `api/v2`
- развернуть систему локально у клиента или в облаке с тем же кодом и тем же PostgreSQL-стеком

## Структура проекта

```text
DataSetAI/
├── manage.py
├── .env.example
├── README.md
├── requirements/
│   ├── base.txt
│   └── local.txt
├── config/
│   ├── urls.py
│   └── settings/
│       ├── base.py
│       └── local.py
├── common/
│   ├── auth.py
│   ├── exceptions.py
│   ├── drf_exception_handler.py
│   └── permissions.py
├── apps/
│   ├── api/v1/urls.py
│   ├── users/
│   ├── rooms/
│   └── labeling/
└── tests/
```

## Быстрый старт

### 1. Поднять PostgreSQL

Локально должен быть доступен PostgreSQL. Пример параметров для локального MVP:

- database: `datasetai`
- user: ваш локальный PostgreSQL user, на macOS часто это имя системного пользователя
- password: зависит от локальной настройки PostgreSQL, часто пустой для локального dev-окружения
- host: `127.0.0.1`
- port: `5432`

Пример создания БД:

```sql
CREATE DATABASE datasetai;
```

Для типичной локальной установки на macOS часто достаточно:

```bash
createdb datasetai
```

### 2. Создать виртуальное окружение и поставить зависимости

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements/local.txt
```

### 3. Подготовить переменные окружения

```bash
cp .env.example .env
```

Проект читает `.env` автоматически при старте Django, поэтому `source .env` не требуется.

Проверь `.env` и укажи реального локального пользователя PostgreSQL. Для твоей машины это, скорее всего, `w`:

```env
POSTGRES_DB=datasetai
POSTGRES_USER=w
POSTGRES_PASSWORD=
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

### 4. Применить миграции

```bash
python3 manage.py migrate
```

### 5. Загрузить seed-данные

```bash
python3 manage.py seed_mvp_data
```

Команда выведет идентификаторы пользователей и комнаты для тестовых запросов.

### 6. Запустить сервер

```bash
python3 manage.py runserver
```

После запуска будут доступны:

- UI: `http://127.0.0.1:8000/`
- health-check: `http://127.0.0.1:8000/health/`
- service info: `http://127.0.0.1:8000/service/`
- API: `http://127.0.0.1:8000/api/v1/`

## Браузерный UI

На корневом маршруте `/` доступен встроенный интерфейс для локального MVP.

Что умеет:

- выбрать mock user из seed-данных или вручную ввести `X-User-Id`
- загрузить rooms для текущего пользователя
- создать room и пригласить annotator как customer
- войти в room, получить следующую задачу и отправить annotation как annotator
- видеть лог API-запросов прямо в интерфейсе

Рекомендуемый сценарий:

1. Выполни `python3 manage.py seed_mvp_data`.
2. Открой `http://127.0.0.1:8000/`.
3. Выбери `customer_demo`, создай room или используй существующую.
4. Пригласи `annotator_alice` или `annotator_bob`.
5. Переключись на annotator, зайди в room и получи `next task`.
6. Отправь `result_payload` через UI.

## Временная идентификация пользователя

Для MVP полноценная аутентификация не реализована.

Сервер определяет пользователя по header:

```text
X-User-Id: <user_id>
```

Роль пользователя не передается снаружи. Она читается только из БД по `User.role`.

Позже этот механизм можно заменить на:

- session auth
- JWT
- корпоративный SSO
- OAuth2/OpenID Connect

без переписывания основного бизнес-слоя.

## Основные endpoint-ы v1

### Заказчик

- `POST /api/v1/rooms/`
- `GET /api/v1/rooms/`
- `GET /api/v1/rooms/{id}/`
- `POST /api/v1/rooms/{id}/invite/`

### Разметчик

- `GET /api/v1/me/rooms/`
- `POST /api/v1/rooms/{id}/join/`
- `GET /api/v1/rooms/{id}/tasks/next/`
- `POST /api/v1/tasks/{id}/submit/`

## Примеры запросов

Ниже предполагается, что после `seed_mvp_data`:

- customer id = `1`
- annotator id = `2`
- room id = `1`

### Создать room как заказчик

```bash
curl -X POST http://127.0.0.1:8000/api/v1/rooms/ \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{
    "title": "Sentiment dataset",
    "description": "Room for initial annotation batch"
  }'
```

### Получить список своих rooms как заказчик

```bash
curl http://127.0.0.1:8000/api/v1/rooms/ \
  -H "X-User-Id: 1"
```

### Пригласить разметчика

```bash
curl -X POST http://127.0.0.1:8000/api/v1/rooms/1/invite/ \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{
    "annotator_id": 2
  }'
```

### Получить свои rooms как разметчик

```bash
curl http://127.0.0.1:8000/api/v1/me/rooms/ \
  -H "X-User-Id: 2"
```

### Войти в room как разметчик

```bash
curl -X POST http://127.0.0.1:8000/api/v1/rooms/1/join/ \
  -H "X-User-Id: 2"
```

### Получить следующую задачу

```bash
curl http://127.0.0.1:8000/api/v1/rooms/1/tasks/next/ \
  -H "X-User-Id: 2"
```

Если доступных задач нет, API возвращает `204 No Content`.

### Отправить результат разметки

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/1/submit/ \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 2" \
  -d '{
    "result_payload": {
      "label": "positive",
      "confidence": 0.93
    }
  }'
```

## Базовые тесты

Запуск:

```bash
python3 manage.py test
```

Покрытые сценарии:

- customer создает room
- customer приглашает annotator
- annotator видит только свои rooms
- annotator не может войти в чужую room
- annotator получает next task
- annotator отправляет annotation
- annotator без joined membership не получает задачу

## Что можно добавить дальше без слома каркаса

- полноценную auth-систему
- отдельную сущность assignment при усложнении жизненного цикла задач
- пагинацию и фильтрацию
- audit logging
- soft delete
- Celery/Redis для фоновых процессов
- Docker и production deployment-пайплайн
