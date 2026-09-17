import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = "django-insecure-local-dev-key-for-the-no-db-banking-api"
DEBUG = True
ALLOWED_HOSTS = ["*"]


INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework.authtoken",
    "corsheaders",
    "rest_framework",
    "banking",
]


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]


CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = []


DATABASES = {
    "default": dj_database_url.parse(os.environ["DATABASE_URL"]),
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
        "rest_framework.authentication.TokenAuthentication",
    ],


    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],

    "EXCEPTION_HANDLER": "banking.errors.api_exception_handler",

    "COERCE_DECIMAL_TO_STRING": False,
}
