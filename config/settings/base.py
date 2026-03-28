import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

"""
Base Django settings shared by local, CI and production environments.

Project convention:
- all runtime configuration comes from environment variables / `.env`
- DB_* settings are mandatory because the whole app depends on PostgreSQL
- media files are stored on disk and must be served by nginx in production
"""


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)


def env(key: str, default=None):
    return os.getenv(key, default)


def env_any(*keys: str, default=None):
    for key in keys:
        value = os.getenv(key)
        if value not in (None, ""):
            return value
    return default


def required_env(*keys: str, label: str | None = None) -> str:
    value = env_any(*keys)
    if value not in (None, ""):
        return value

    setting_name = label or keys[0]
    displayed_keys = ", ".join(keys)
    raise ImproperlyConfigured(
        f"{setting_name} is not configured. Copy .env.example to .env and set "
        f"{displayed_keys} before starting the project."
    )


def env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(key: str, default: str = "") -> list[str]:
    value = os.getenv(key, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def validate_database_configuration() -> None:
    # CI can provide POSTGRES_* directly; local and production usually use DB_*.
    required_specs = {
        "DB_NAME": ("DB_NAME", "POSTGRES_DB"),
        "DB_USER": ("DB_USER", "POSTGRES_USER"),
        "DB_PASSWORD": ("DB_PASSWORD", "POSTGRES_PASSWORD"),
        "DB_HOST": ("DB_HOST", "POSTGRES_HOST"),
        "DB_PORT": ("DB_PORT", "POSTGRES_PORT"),
    }
    missing = [
        label for label, keys in required_specs.items() if env_any(*keys) in (None, "")
    ]

    if not ENV_FILE.exists() and missing:
        missing_values = ", ".join(missing)
        raise ImproperlyConfigured(
            f"Configuration file {ENV_FILE.name} was not found and required "
            f"database settings are missing: {missing_values}. Copy .env.example "
            "to .env or export the variables before running Django."
        )

    if missing == ["DB_PASSWORD"]:
        raise ImproperlyConfigured(
            "DB_PASSWORD is not configured. Copy .env.example to .env and fill in "
            "the database password provided for the SSH tunnel."
        )

    if missing:
        missing_values = ", ".join(missing)
        raise ImproperlyConfigured(
            f"Required database settings are missing: {missing_values}. Update .env "
            "before starting the project."
        )


validate_database_configuration()


SECRET_KEY = env("DJANGO_SECRET_KEY", "unsafe-local-secret-key")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.ui",
    "apps.users",
    "apps.rooms",
    "apps.labeling",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.ApiExceptionMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required_env("DB_NAME", "POSTGRES_DB", label="DB_NAME"),
        "USER": required_env("DB_USER", "POSTGRES_USER", label="DB_USER"),
        "PASSWORD": required_env("DB_PASSWORD", "POSTGRES_PASSWORD", label="DB_PASSWORD"),
        "HOST": required_env("DB_HOST", "POSTGRES_HOST", label="DB_HOST"),
        "PORT": required_env("DB_PORT", "POSTGRES_PORT", label="DB_PORT"),
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = env("LANGUAGE_CODE", "en-us")
TIME_ZONE = env("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
# Image/video task sources are persisted here. Django serves them only in DEBUG,
# so production must expose this directory through nginx.
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"
LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/rooms/"
LOGOUT_REDIRECT_URL = "/"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "common.auth.HeaderUserAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Keep `format` available for business query params such as export format.
    "URL_FORMAT_OVERRIDE": None,
    "EXCEPTION_HANDLER": "common.drf_exception_handler.custom_exception_handler",
}
