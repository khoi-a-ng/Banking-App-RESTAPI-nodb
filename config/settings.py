from pathlib import Path



BASE_DIR = Path(__file__).resolve().parent.parent

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


DATABASES = {}

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
