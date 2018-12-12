import os

test_db_name = os.environ.get("DJSTRIPE_TEST_DB_NAME", "djstripe")
test_db_user = os.environ.get("DJSTRIPE_TEST_DB_USER", "postgres")
test_db_pass = os.environ.get("DJSTRIPE_TEST_DB_PASS", "")

DEBUG = True
SECRET_KEY = "djstripe"
SITE_ID = 1
TIME_ZONE = "UTC"
USE_TZ = True
DATABASES = {
	"default": {
		"ENGINE": "django.db.backends.postgresql_psycopg2",
		"NAME": test_db_name,
		"USER": test_db_user,
		"PASSWORD": test_db_pass,
		"HOST": "localhost",
		"PORT": "",
	}
}

TEMPLATES = [
	{
		"BACKEND": "django.template.backends.django.DjangoTemplates",
		"DIRS": [],
		"APP_DIRS": True,
		"OPTIONS": {
			"context_processors": [
				"django.contrib.auth.context_processors.auth",
				"django.contrib.messages.context_processors.messages",
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
	"jsonfield",
	"djstripe",
	"tests",
	"tests.apps.testapp",
]

MIDDLEWARE = (
	"django.contrib.sessions.middleware.SessionMiddleware",
	"django.contrib.auth.middleware.AuthenticationMiddleware",
	"django.contrib.messages.middleware.MessageMiddleware",
)

STRIPE_LIVE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "pk_test_123")
STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_123")
STRIPE_TEST_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "pk_test_123")
STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_123")

# TODO - these seem to be unused, remove?
DJSTRIPE_PLANS = {
	"test0": {
		"stripe_plan_id": "test_id_0",
		"name": "Test Plan 0",
		"description": "A test plan",
		"price": 1000,  # $10.00
		"currency": "usd",
		"interval": "month",
	},
	"test": {
		"stripe_plan_id": "test_id",
		"name": "Test Plan 1",
		"description": "Another test plan",
		"price": 2500,  # $25.00
		"currency": "usd",
		"interval": "month",
	},
	"test2": {
		"stripe_plan_id": "test_id_2",
		"name": "Test Plan 2",
		"description": "Yet Another test plan",
		"price": 5000,  # $50.00
		"currency": "usd",
		"interval": "month",
	},
	"test_deletion": {
		"stripe_plan_id": "test_id_3",
		"name": "Test Plan 3",
		"description": "Test plan for deletion.",
		"price": 5000,  # $50.00
		"currency": "usd",
		"interval": "month",
	},
	"test_trial": {
		"stripe_plan_id": "test_id_4",
		"name": "Test Plan 4",
		"description": "Test plan for trails.",
		"price": 7000,  # $70.00
		"currency": "usd",
		"interval": "month",
		"trial_period_days": 7,
	},
	"unidentified_test_plan": {
		"name": "Unidentified Test Plan",
		"description": "A test plan with no ID.",
		"price": 2500,  # $25.00
		"currency": "usd",
		"interval": "month",
	},
}

DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS = (
	"(admin)",
	"test_url_name",
	"testapp_namespaced:test_url_namespaced",
	"fn:/test_fnmatch*",
)

DJSTRIPE_USE_NATIVE_JSONFIELD = os.environ.get("USE_NATIVE_JSONFIELD", "") == "1"
DJSTRIPE_SUBSCRIPTION_REDIRECT = "test_url_subscribe"
DJSTRIPE_WEBHOOK_VALIDATION = "verify_signature"
DJSTRIPE_WEBHOOK_SECRET = "whsec_XXXXX"
