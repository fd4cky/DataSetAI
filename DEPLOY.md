# Deploy Guide

Этот документ описывает, как команда работает с production для проекта DataSetAI.

## Как теперь устроен процесс

1. Разработчик создаёт отдельную ветку от `main`.
2. Делает изменения локально.
3. Локально проверяет проект.
4. Пушит ветку в GitHub.
5. Создаёт Pull Request в `main`.
6. GitHub Actions запускает CI:
   - `python manage.py check`
   - `python manage.py test`
7. После merge в `main` GitHub Actions запускает production deploy.
8. Сервер выполняет `/srv/datasetai/deploy.sh`.
9. Django-сервис перезапускается автоматически.

## Что должен делать разработчик

Обычный цикл работы:

```bash
git checkout main
git pull
git checkout -b feature/my-change
```

После изменений:

```bash
git add <files>
git commit -m "Describe your change"
git push -u origin feature/my-change
```

Дальше:

1. Создать PR в `main`
2. Дождаться зелёного CI
3. Сделать merge

## Как тестировать локально

Каждый участник команды тестирует проект локально, без доступа к production-серверу.

Базовый цикл:

```bash
python -m venv .venv
python -m pip install -r requirements/local.txt
python manage.py migrate
python manage.py runserver
```

Если нужны тестовые данные:

```bash
python manage.py seed_mvp_data
```

Проверки перед PR:

```bash
python manage.py check
python manage.py test
```

## Что делает CI

Workflow `Run CI` запускается на каждый Pull Request в `main`.

Он:

1. Поднимает временный PostgreSQL в GitHub Actions
2. Устанавливает зависимости
3. Запускает `python manage.py check`
4. Запускает `python manage.py test`

Если CI красный, PR не должен мержиться.

## Что делает production deploy

Workflow `Deploy To Production` запускается только после `push` в `main`.

Он:

1. Подключается по SSH на production-сервер
2. Вызывает `/srv/datasetai/deploy.sh`

Скрипт на сервере делает:

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

## Полезные команды на сервере

Статус Django-сервиса:

```bash
sudo systemctl status datasetai --no-pager -l
```

Логи Django-сервиса:

```bash
sudo journalctl -u datasetai -n 100 --no-pager
```

Перезапуск Django-сервиса:

```bash
sudo systemctl restart datasetai
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

Проверка локального ответа приложения на сервере:

```bash
curl -I -H "Host: <server_ip_or_domain>" http://127.0.0.1
```

Проверка внешнего ответа:

```bash
curl -I http://<server_ip_or_domain>
```

Ручной deploy на сервере:

```bash
sudo -u datasetai /srv/datasetai/deploy.sh
```

## Что делать, если deploy упал

1. Открыть `Actions` в GitHub
2. Найти упавший workflow `Deploy To Production`
3. Посмотреть шаг, на котором произошла ошибка
4. Если SSH не работает:
   - проверить GitHub Secrets
   - проверить ключ в `/srv/datasetai/.ssh/authorized_keys`
5. Если код задеплоился, но сайт не отвечает:
   - проверить `datasetai`
   - проверить `nginx`
   - посмотреть логи через `journalctl`

## Что делать, если CI упал

1. Открыть `Actions` в GitHub
2. Найти workflow `Run CI`
3. Посмотреть, падает ли:
   - установка зависимостей
   - `manage.py check`
   - `manage.py test`
4. Исправить проблему локально
5. Снова запушить ветку

## Правила для команды

- Не пушить напрямую в `main`
- Все изменения делать через Pull Request
- Не хранить секреты в git
- Не редактировать production-сервер руками без необходимости
- Сначала чинить локально и в PR, потом деплоить

## Следующие улучшения

Когда базовый workflow стабилизируется, следующий шаг:

1. Настроить HTTPS через Let's Encrypt
2. Добавить staging
3. Добавить резервные копии базы
4. Добавить мониторинг и алерты
