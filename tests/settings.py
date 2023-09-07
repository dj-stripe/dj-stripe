import json
import os

test_db_vendor = os.environ.get("DJSTRIPE_TEST_DB_VENDOR", "postgres")
test_db_name = os.environ.get("DJSTRIPE_TEST_DB_NAME", "djstripe")
test_db_user = os.environ.get("DJSTRIPE_TEST_DB_USER", test_db_vendor)
test_db_pass = os.environ.get("DJSTRIPE_TEST_DB_PASS", "djstripe")
test_db_port = os.environ.get("DJSTRIPE_TEST_DB_PORT", "")

DEBUG = True
SECRET_KEY = os.environ.get("DJSTRIPE_TEST_DJANGO_SECRET_KEY", "djstripe")
SITE_ID = 1
TIME_ZONE = "UTC"
USE_TZ = True
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PROJECT_DIR)

ALLOWED_HOSTS = json.loads(os.environ.get("DJSTRIPE_TEST_ALLOWED_HOSTS_JSON", '["*"]'))

if test_db_vendor == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": test_db_name,
            "USER": test_db_user,
            "PASSWORD": test_db_pass,
            "HOST": os.environ.get("DJSTRIPE_TEST_DB_HOST", "localhost"),
            "PORT": test_db_port,
        }
    }
elif test_db_vendor == "mysql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": test_db_name,
            "USER": os.environ.get("DJSTRIPE_TEST_DB_USER", "root"),
            "PASSWORD": test_db_pass,
            "HOST": os.environ.get("DJSTRIPE_TEST_DB_HOST", "127.0.0.1"),
            "PORT": test_db_port,
        }
    }
elif test_db_vendor == "sqlite":
    # sqlite is not officially supported, but useful for quick testing.
    # may be dropped if we can't maintain compatibility.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
            # use a on-disk db for test so --reuse-db can be used
            "TEST": {"NAME": os.path.join(BASE_DIR, "test_db.sqlite3")},
        }
    }
else:
    raise NotImplementedError(f"DJSTRIPE_TEST_DB_VENDOR = {test_db_vendor}")


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
            ]
        },
    }
]

ROOT_URLCONF = "tests.urls"
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "djstripe",
    "tests",
    # to load custom models defined to test fields.py
    "tests.fields",
    "tests.apps.testapp",
    "tests.apps.example",
]

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

STRIPE_LIVE_PUBLIC_KEY = os.environ.get(
    "STRIPE_PUBLIC_KEY", "pk_live_XXXXXXXXXXXXXXXXXXXXXXXXX"
)
STRIPE_LIVE_SECRET_KEY = os.environ.get(
    "STRIPE_SECRET_KEY", "sk_live_XXXXXXXXXXXXXXXXXXXXXXXXX"
)
STRIPE_TEST_PUBLIC_KEY = os.environ.get(
    "STRIPE_PUBLIC_KEY",
    "pk_test_XXXXXXXXXXXXXXXXXXXXXXXXX",
)
STRIPE_TEST_SECRET_KEY = os.environ.get(
    "STRIPE_SECRET_KEY",
    "sk_test_XXXXXXXXXXXXXXXXXXXXXXXXX",
)

DJSTRIPE_FOREIGN_KEY_TO_FIELD = (
    "id" if os.environ.get("USE_NATIVE_STRIPE_ID", "") == "1" else "djstripe_id"
)

DJSTRIPE_WEBHOOK_VALIDATION = "verify_signature"

STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
