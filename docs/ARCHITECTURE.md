# Архитектура DataSetAI

Этот документ описывает, как устроен проект на уровне модулей, сущностей и основных потоков данных.

## Общая схема

DataSetAI построен как монолитное Django-приложение с серверным UI и REST API.

Основной поток выглядит так:

1. Пользователь открывает UI в браузере
2. Django templates рендерят страницы
3. UI обращается к API `/api/v1/...`
4. Django и DRF работают с PostgreSQL
5. Для image/video задач исходные файлы сохраняются в `MEDIA_ROOT`
6. В production `nginx` отдаёт `static` и `media`, а `gunicorn` обслуживает Django

## Основные приложения

### `apps.ui`

Отвечает за серверные HTML-страницы и публичные/пользовательские view:

- landing page
- login / register
- список комнат
- создание комнаты
- рабочее пространство комнаты
- health и service endpoints

Ключевой файл: [apps/ui/views.py](../apps/ui/views.py)

### `apps.users`

Отвечает за пользователя и management commands.

Ключевые элементы:

- кастомная модель пользователя `User`
- роль пользователя через поле `role`
- команды:
  - `create_local_user`
  - `seed_mvp_data`

Ключевые файлы:

- [apps/users/models.py](../apps/users/models.py)
- [apps/users/management/commands/create_local_user.py](../apps/users/management/commands/create_local_user.py)
- [apps/users/management/commands/seed_mvp_data.py](../apps/users/management/commands/seed_mvp_data.py)

### `apps.rooms`

Домен комнат для разметки.

Основные сущности:

- `Room` - комната разметки
- `RoomLabel` - список доступных меток
- `RoomMembership` - приглашение и участие пользователя в комнате

Поддерживаемые типы датасетов:

- `demo`
- `json`
- `image`
- `video`

Ключевой файл: [apps/rooms/models.py](../apps/rooms/models.py)

### `apps.labeling`

Домен задач и аннотаций.

Основные сущности:

- `Task` - элемент датасета для разметки
- `TaskAssignment` - назначение задачи аннотатору
- `Annotation` - результат разметки

Поддерживаемые типы источников:

- `text`
- `image`
- `video`

Для image/video задач используется `source_file`, который сохраняется в `MEDIA_ROOT`.

Ключевой файл: [apps/labeling/models.py](../apps/labeling/models.py)

### `apps.api`

Точка сборки API v1. Подключает маршруты из доменных приложений.

Ключевой файл: [apps/api/v1/urls.py](../apps/api/v1/urls.py)

### `common`

Общая инфраструктура проекта:

- базовые модели
- authentication helpers
- middleware
- DRF exception handling
- общие error views

## Ключевые сущности и связи

### Пользователь

Пользователь хранится в модели `User` и может:

- создавать комнаты
- быть приглашённым в комнаты
- получать назначения на задачи
- отправлять аннотации

### Комната

Комната объединяет:

- создателя
- участников
- метки
- задачи
- настройки cross-validation

### Участие в комнате

`RoomMembership` фиксирует участие пользователя в комнате и его состояние:

- `invited`
- `joined`

Это важно для контроля доступа и join-flow.

### Задача

`Task` относится к комнате и может содержать:

- `input_payload` для текстовых/JSON-задач
- `source_file` для image/video
- `source_name`
- статус и текущий раунд

### Назначение

`TaskAssignment` связывает:

- задачу
- аннотатора
- раунд
- статус выполнения

### Аннотация

`Annotation` хранит результат разметки по задаче и связана с:

- задачей
- назначением
- аннотатором

## URL-слои

### UI

Основные страницы подключаются через:

- [config/urls.py](../config/urls.py)
- `apps.ui.urls`

Публичные сервисные endpoints:

- `/health/`
- `/service/`

### API

API v1 подключается по префиксу:

- `/api/v1/`

Маршруты собираются из:

- `apps.rooms.api.v1.urls`
- `apps.labeling.api.v1.urls`
- `apps.users.api.v1.urls`

## Конфигурация окружения

Проект читает настройки из `.env` через `python-dotenv`.

Обязательные параметры БД:

- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

Если `.env` отсутствует или обязательные `DB_*` не заданы, Django завершится с `ImproperlyConfigured`.

Ключевой файл: [config/settings/base.py](../config/settings/base.py)

## Static и media

### Static

- `STATIC_URL = /static/`
- `STATIC_ROOT = <repo>/staticfiles`

В production static-файлы отдаёт `nginx`.

### Media

- `MEDIA_URL = /media/`
- `MEDIA_ROOT = <repo>/media`

Важно:

- при `DEBUG=true` media обслуживается Django
- в production media обязан отдавать `nginx`
- для image/video задач сервер должен уметь принимать большие upload-запросы

## CI/CD

### CI

Workflow [ci.yml](../.github/workflows/ci.yml):

- запускается на каждый Pull Request в `main`
- поднимает временный PostgreSQL 14
- выполняет `python manage.py check`
- выполняет `python manage.py test`

### Production deploy

Workflow [deploy.yml](../.github/workflows/deploy.yml):

- запускается на `push` в `main`
- подключается по SSH к production-серверу
- вызывает `/srv/datasetai/deploy.sh`

## Production-контур

В production используются:

- `gunicorn` как app server
- `systemd` как менеджер сервиса
- `nginx` как reverse proxy и TLS termination
- PostgreSQL на том же сервере
- HTTPS на домене `p-dataset.ru`

Подробности эксплуатации лежат в [../DEPLOY.md](../DEPLOY.md).
