# Deploy Guide

Этот документ описывает текущий production-контур проекта DataSetAI и правила работы с ним.

## Production в текущем виде

Сейчас production состоит из следующих частей:

- домен: `p-dataset.ru`
- HTTPS: настроен через `certbot` и `nginx`
- сервер: Ubuntu 22.04
- приложение: Django + `gunicorn`
- reverse proxy: `nginx`
- управление сервисом: `systemd`
- база данных: PostgreSQL 14 на том же сервере
- CI/CD: GitHub Actions

## Как работает командный процесс

1. Разработчик создаёт ветку от `main`
2. Делает изменения локально
3. Проверяет проект локально
4. Пушит ветку на GitHub
5. Создаёт Pull Request в `main`
6. GitHub Actions запускает CI
7. После merge в `main` GitHub Actions запускает production deploy
8. Сервер выполняет `/srv/datasetai/deploy.sh`
9. `datasetai` перезапускается автоматически

## Что делает CI

Workflow [ci.yml](.github/workflows/ci.yml) запускается на каждый Pull Request в `main`.

Он:

1. Поднимает временный PostgreSQL 14 в GitHub Actions
2. Устанавливает зависимости
3. Выполняет `python manage.py check`
4. Выполняет `python manage.py test`

Если CI красный, PR не должен мержиться.

## Что делает production deploy

Workflow [deploy.yml](.github/workflows/deploy.yml) запускается только после `push` в `main`.

Он:

1. Создаёт SSH-ключ из `SSH_PRIVATE_KEY_B64`
2. Проверяет SSH-доступ к серверу
3. Подключается к серверу под пользователем `datasetai`
4. Вызывает `/srv/datasetai/deploy.sh`

Серверный deploy script выполняет:

1. `git pull origin main`
2. установку зависимостей
3. `python manage.py migrate`
4. `python manage.py collectstatic --noinput`
5. `systemctl restart datasetai`

## Важные пути на сервере

- Код проекта: `/srv/datasetai/app`
- Virtualenv: `/srv/datasetai/venv`
- Deploy script: `/srv/datasetai/deploy.sh`
- Django service: `datasetai`
- Nginx config: `/etc/nginx/sites-available/datasetai`
- Сертификаты Let's Encrypt: стандартные пути `certbot` в `/etc/letsencrypt/`

## Production-конфигурация приложения

### `.env`

Production `.env` лежит на сервере и не хранится в git.

Типовой состав:

```env
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=p-dataset.ru,www.p-dataset.ru,46.16.36.87
TIME_ZONE=UTC

DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=127.0.0.1
DB_PORT=5432
```

Важно:

- на production приложение ходит в PostgreSQL напрямую на `127.0.0.1:5432`
- SSH-туннель для production не нужен

### Static и media

В production:

- `static` отдаёт `nginx`
- `media` тоже отдаёт `nginx`

Это обязательно для image/video задач, потому что Django не обслуживает media при `DEBUG=false`.

### Upload для image/video

Для image/video задач production должен поддерживать:

- каталог `media/` с правом записи для `datasetai`
- `location /media/` в `nginx`
- достаточный `client_max_body_size`

Пример важных блоков в nginx:

```nginx
client_max_body_size 200M;

location /static/ {
    alias /srv/datasetai/app/staticfiles/;
}

location /media/ {
    alias /srv/datasetai/app/media/;
}
```

Если этих настроек нет, создание image/video задач может падать даже при исправном Python-коде.

## Как разработчику тестировать локально

Участникам команды не нужен доступ к production-серверу для повседневной разработки.

Обычный локальный цикл:

```bash
python -m venv .venv
python -m pip install -r requirements/local.txt
python manage.py migrate
python manage.py runserver
```

При необходимости:

```bash
python manage.py seed_mvp_data
python manage.py check
python manage.py test
```

Если используется удалённая dev-база, доступ к ней делается через SSH-туннель.

## Полезные команды на сервере

Статус Django-сервиса:

```bash
sudo systemctl status datasetai --no-pager -l
```

Логи Django-сервиса:

```bash
sudo journalctl -u datasetai -n 100 --no-pager
```

Статус nginx:

```bash
sudo systemctl status nginx --no-pager
```

Проверка nginx-конфига:

```bash
sudo nginx -t
```

Перезапуск nginx:

```bash
sudo systemctl restart nginx
```

Проверка ответа приложения локально на сервере:

```bash
curl -I -H "Host: p-dataset.ru" http://127.0.0.1
```

Проверка внешнего ответа:

```bash
curl -I https://p-dataset.ru
```

Ручной pull кода:

```bash
cd /srv/datasetai/app
sudo -u datasetai git pull
```

Ручной deploy:

```bash
sudo -u datasetai /srv/datasetai/deploy.sh
```

Миграции вручную:

```bash
cd /srv/datasetai/app
sudo -u datasetai /srv/datasetai/venv/bin/python manage.py migrate
```

Проверка БД вручную:

```bash
cd /srv/datasetai/app
sudo -u datasetai /srv/datasetai/venv/bin/python scripts/check_db.py
```

## Что делать, если deploy упал

1. Открыть вкладку `Actions` в GitHub
2. Найти упавший workflow `Deploy To Production`
3. Посмотреть шаг, на котором произошла ошибка

Типовые причины:

- неверные GitHub Secrets
- проблема с SSH-ключом
- ошибка внутри `/srv/datasetai/deploy.sh`
- миграции или `collectstatic` упали
- `datasetai` не поднялся после перезапуска

После этого проверить:

```bash
sudo systemctl status datasetai --no-pager -l
sudo journalctl -u datasetai -n 100 --no-pager
```

## Что делать, если CI упал

1. Открыть вкладку `Actions`
2. Найти workflow `Run CI`
3. Посмотреть, на каком шаге произошла ошибка

Чаще всего падает одно из:

- установка зависимостей
- `python manage.py check`
- `python manage.py test`

Правильный порядок действий:

1. воспроизвести проблему локально
2. исправить её в своей ветке
3. запушить изменения
4. дождаться нового зелёного CI

## Что делать, если сайт не отвечает

Проверить последовательно:

1. `datasetai`
2. `nginx`
3. локальный ответ `gunicorn`
4. внешний ответ по домену
5. срок сертификата и HTTPS-конфиг

Команды:

```bash
sudo systemctl status datasetai --no-pager -l
sudo systemctl status nginx --no-pager
curl -I -H "Host: p-dataset.ru" http://127.0.0.1
curl -I https://p-dataset.ru
```

## Что делать, если не работают image/video загрузки

Проверить:

1. существует ли каталог `/srv/datasetai/app/media`
2. может ли `datasetai` писать в `media`
3. есть ли `location /media/` в nginx
4. достаточен ли `client_max_body_size`
5. что пишет `/var/log/nginx/error.log`
6. что пишет `journalctl -u datasetai`

Типовые симптомы:

- `413 Request Entity Too Large` - слишком маленький upload limit в nginx
- `Permission denied` - неправильные права на `media`
- 404 на media URL - отсутствует `location /media/`

## Правила для команды

- не пушить напрямую в `main`
- все изменения делать через Pull Request
- не хранить секреты в git
- не редактировать production руками без необходимости
- сначала чинить проблему локально и в PR, потом деплоить
