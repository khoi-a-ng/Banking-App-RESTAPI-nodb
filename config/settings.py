import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Reads the .env file at the project root (never committed — see .gitignore)
# so DATABASE_URL doesn't have to be hardcoded here.
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = "django-insecure-local-dev-key-for-the-no-db-banking-api"
DEBUG = True
ALLOWED_HOSTS = ["*"]


INSTALLED_APPS = [
    "rest_framework",
    "banking",
]


MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]


ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = []


# dj_database_url.parse turns the single connection string from Supabase
# into the dict-of-settings shape Django's DATABASES expects (HOST, PORT,
# USER, PASSWORD, etc. as separate keys) instead of parsing the URL by hand.
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

    "DEFAULT_AUTHENTICATION_CLASSES": [],

    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],

    "UNAUTHENTICATED_USER": None,

    "EXCEPTION_HANDLER": "banking.errors.api_exception_handler",

    "COERCE_DECIMAL_TO_STRING": False,
}
