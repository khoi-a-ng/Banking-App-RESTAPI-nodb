import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Reads .env locally. On Lambda there is no .env file -- the same names are
# supplied as real environment variables instead, and load_dotenv simply does
# nothing when the file is missing.
load_dotenv(BASE_DIR / ".env")


def env_flag(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes"}


def env_list(name: str) -> list[str]:
    """Comma-separated env var -> list. Empty string means empty list."""
    raw = os.environ.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


DEBUG = env_flag("DJANGO_DEBUG", "true")

# The signing key for every JWT this API issues (see SIGNING_KEY below), so a
# leaked value means anybody can forge a token for any user. It must come from
# the environment in production; the fallback exists only so local development
# and the test suite keep working without extra setup.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off."
        )
    SECRET_KEY = "django-insecure-local-dev-key-do-not-deploy"

# Lambda sits behind API Gateway, which supplies its own host header.
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS") or ["*"]

# API Gateway terminates TLS and forwards the original scheme in this header;
# without it Django thinks every request arrived over plain http.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "banking",
]


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]


# In production this is the CloudFront URL the React build is served from.
# Locally it falls back to the Vite dev server.
CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ORIGINS") or [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = []


DATABASES = {

    "default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=0),
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


REST_FRAMEWORK = {

    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],

    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],


    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],


    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],

    "EXCEPTION_HANDLER": "banking.errors.api_exception_handler",

    "COERCE_DECIMAL_TO_STRING": False,
}



SIMPLE_JWT = {

    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),

    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    "ROTATE_REFRESH_TOKENS": True,

    "BLACKLIST_AFTER_ROTATION": True,

    "AUTH_HEADER_TYPES": ("Bearer",),

    "SIGNING_KEY": SECRET_KEY,
}
