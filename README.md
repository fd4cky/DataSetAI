# DataSetAI

Django backend для платформы разметки датасетов. PostgreSQL на сервере остаётся закрытым наружу и доступен только через локальный SSH-туннель.

Схема подключения:

```text
localhost:6543 -> SSH tunnel -> server:127.0.0.1:5432
```

`.env` не хранится в git. В репозитории живут только шаблон и код, а реальные параметры БД разработчик заполняет локально.

## Быстрый старт

1. Клонируй репозиторий.

```bash
git clone <repo-url>
cd DataSetAI
```

2. Создай виртуальное окружение.

```bash
python -m venv .venv
```

3. Активируй окружение.

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

4. Установи зависимости.

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements/local.txt
```

5. Создай `.env`.

```bash
# macOS / Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

6. Заполни `.env`.

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

7. Подними SSH-туннель в отдельном терминале.

```powershell
ssh -N -L 6543:127.0.0.1:5432 <ssh_user>@<server_ip>
```

8. Проверь подключение к базе.

```bash
python scripts/check_db.py
```

9. Примени миграции.

```bash
python manage.py migrate
```

10. При необходимости загрузи тестовые данные.

```bash
python manage.py seed_mvp_data
```

11. Запусти проект.

```bash
python manage.py runserver
```

После запуска приложение доступно на `http://127.0.0.1:8000/`.

## Упрощённый bootstrap

Если есть Bash, можно сократить шаги 2-5 одной командой:

```bash
bash bin/bootstrap_local.sh
```

Скрипт:

- создаёт `.venv`, если его ещё нет
- ставит зависимости
- создаёт `.env` из `.env.example`, если файла ещё нет

После этого всё равно нужно заполнить `.env`, открыть SSH-туннель отдельной командой и только потом запускать Django.

## Что лежит в `.env.example`

```env
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=6543
```

Все `DB_*` значения обязательны. Если `.env` отсутствует или в нём не заполнены обязательные значения, Django завершится с понятной ошибкой на старте. Для `DB_PASSWORD` сообщение отдельное и явное.

## Полезные команды

```bash
python scripts/check_db.py
python manage.py migrate
python manage.py seed_mvp_data
python manage.py create_local_user alice strongpass123 --email alice@example.com
python manage.py runserver
python manage.py test
```

## Структура проекта

- `config/` - Django settings, URLs, ASGI/WSGI
- `apps/` - доменные приложения
- `common/` - общая инфраструктура
- `scripts/` - служебные скрипты для локальной разработки
- `bin/` - bootstrap-скрипты
