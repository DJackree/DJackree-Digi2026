"""Django settings for Telecom Customer Portal (Phase 1 foundation)."""

import os
from pathlib import Path

from django.contrib.messages import constants as message_constants

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-change-me-for-production")

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "customers",
    "complaints",
    "network",
    "dashboard",
    "chatbot",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Phase 2: authentication and role routing ---
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:home"
LOGOUT_REDIRECT_URL = "accounts:login"

_csrf_origins = os.environ.get(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000",
)
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in _csrf_origins.split(",") if origin.strip()]

MESSAGE_TAGS = {
    message_constants.DEBUG: "secondary",
    message_constants.INFO: "info",
    message_constants.SUCCESS: "success",
    message_constants.WARNING: "warning",
    message_constants.ERROR: "danger",
}

# --- AI chatbot (Phase 2) ---
GROQ_API_KEY = (os.environ.get("GROQ_API_KEY") or "").strip() or None
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_TIMEOUT_SECONDS = float(os.environ.get("GROQ_TIMEOUT_SECONDS", "30"))
GROQ_MAX_COMPLETION_TOKENS = int(os.environ.get("GROQ_MAX_COMPLETION_TOKENS", "512"))
CHATBOT_MESSAGE_MAX_LENGTH = int(os.environ.get("CHATBOT_MESSAGE_MAX_LENGTH", "1000"))
CHATBOT_RECENT_MESSAGE_COUNT = int(os.environ.get("CHATBOT_RECENT_MESSAGE_COUNT", "8"))
CHATBOT_DEFAULT_CURRENCY = os.environ.get("CHATBOT_DEFAULT_CURRENCY", "JMD")

