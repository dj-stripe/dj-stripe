"""
If having trouble due to system clock not being UTC, set this env before running runtests:
       DJSTRIPE_TESTS_SKIP_UTC_TESTS="True"

If you need to skip the coverage test (e.g. it apparently interferes with the debugger in PyCharm):
       DJSTRIPE_TESTS_SKIP_COVERAGE="True"

If you need to skip the pep8 test
       DJSTRIPE_TESTS_SKIP_PEP8="True"


Rather than making these options permanent in your environment, it is recommended you run like this (which sets env
for just one command):

   DJSTRIPE_TESTS_SKIP_COVERAGE=True python runtests.py


---
Why are these environment variables and not command line options?? Because cmd line options are hard/impossible/hack
when using nosetests (according to various online discussions on the topic).
---
"""

from distutils.util import strtobool

import os
import sys

import django
from django.conf import settings

from coverage import coverage
from termcolor import colored

disable_coverage = strtobool(os.environ.get('DJSTRIPE_TESTS_SKIP_COVERAGE', "False"))
disable_pep8 = strtobool(os.environ.get('DJSTRIPE_TESTS_SKIP_PEP8', "False"))

if not disable_coverage:
    cov = coverage(config_file=True)
    cov.erase()
    cov.start()

TESTS_THRESHOLD = 100
TESTS_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

settings.configure(
    TIME_ZONE='America/Los_Angeles',
    DEBUG=True,
    USE_TZ=True,
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": "djstripe",
            "USER": "",
            "PASSWORD": "",
            "HOST": "",
            "PORT": "",
        },
    },
    ROOT_URLCONF="tests.test_urls",
    INSTALLED_APPS=[
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.sites",
        "jsonfield",
        "djstripe",
        "tests",
        "tests.apps.testapp"
    ],
    MIDDLEWARE_CLASSES=(
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware"
    ),
    NOSE_PLUGINS = ['nose.plugins.skip.Skip', ],
    SITE_ID=1,
    STRIPE_PUBLIC_KEY=os.environ.get("STRIPE_PUBLIC_KEY", ""),
    STRIPE_SECRET_KEY=os.environ.get("STRIPE_SECRET_KEY", ""),
    DJSTRIPE_PLANS={
        "test0": {
            "stripe_plan_id": "test_id_0",
            "name": "Test Plan 0",
            "description": "A test plan",
            "price": 1000,  # $10.00
            "currency": "usd",
            "interval": "month"
        },
        "test": {
            "stripe_plan_id": "test_id",
            "name": "Test Plan 1",
            "description": "Another test plan",
            "price": 2500,  # $25.00
            "currency": "usd",
            "interval": "month"
        },
        "test2": {
            "stripe_plan_id": "test_id_2",
            "name": "Test Plan 2",
            "description": "Yet Another test plan",
            "price": 5000,  # $50.00
            "currency": "usd",
            "interval": "month"
        },
        "test_deletion": {
            "stripe_plan_id": "test_id_3",
            "name": "Test Plan 3",
            "description": "Test plan for deletion.",
            "price": 5000,  # $50.00
            "currency": "usd",
            "interval": "month"
        },
        "test_trial": {
            "stripe_plan_id": "test_id_4",
            "name": "Test Plan 4",
            "description": "Test plan for trails.",
            "price": 7000,  # $70.00
            "currency": "usd",
            "interval": "month",
            "trial_period_days": 7
        },
        "unidentified_test_plan": {
            "name": "Unidentified Test Plan",
            "description": "A test plan with no ID.",
            "price": 2500,  # $25.00
            "currency": "usd",
            "interval": "month"
        }
    },
    DJSTRIPE_PLAN_HIERARCHY = {
        "bronze": {
            "level": 1,
            "plans": [
                "test0",
                "test",
            ]
        },
        "silver": {
            "level": 2,
            "plans": [
                "test2",
                "test_deletion",
            ]
        },
        "gold": {
            "level": 3,
            "plans": [
                "test_trial",
                "unidentified_test_plan",
            ]
        },
    },
    DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS=(
        "(admin)",
        "test_url_name",
        "testapp_namespaced:test_url_namespaced",
    ),
)

# Avoid AppRegistryNotReady exception
# http://stackoverflow.com/questions/24793351/django-appregistrynotready
if hasattr(django, "setup"):
    django.setup()

# Announce the test suite
sys.stdout.write(colored(text="\nWelcome to the ", color="magenta", attrs=["bold"]))
sys.stdout.write(colored(text="dj-stripe", color="green", attrs=["bold"]))
sys.stdout.write(colored(text=" test suite.\n\n", color="magenta", attrs=["bold"]))

# Announce test run
sys.stdout.write(colored(text="Step 1: Running unit tests.\n\n", color="yellow", attrs=["bold"]))

from django_nose import NoseTestSuiteRunner

test_runner = NoseTestSuiteRunner(verbosity=1)
failures = test_runner.run_tests(["."])

if failures:
    sys.exit(failures)

if not disable_coverage:
    # Announce coverage run
    sys.stdout.write(colored(text="\nStep 2: Generating coverage results.\n\n", color="yellow", attrs=["bold"]))

    cov.stop()
    percentage = round(cov.report(show_missing=True), 2)
    cov.html_report(directory='cover')
    cov.save()

    if percentage < TESTS_THRESHOLD:
                sys.stderr.write(colored(text="YOUR CHANGES HAVE CAUSED TEST COVERAGE TO DROP. " +
                                         "WAS {old}%, IS NOW {new}%.\n\n".format(old=TESTS_THRESHOLD, new=percentage),
                                         color="red", attrs=["bold"]))
                sys.exit(1)
else:
    sys.stdout.write(colored(text="\nStep 2: Generating coverage results: SKIPPED due to environment "
                                  "variable setting! \n\n", color="yellow", attrs=["bold"]))


if disable_pep8:
    sys.stdout.write(colored(text="\nStep 3: Checking for pep8 errors. SKIPPED due to environment "
                                  "variable setting!\n\n", color="yellow", attrs=["bold"]))
else:
    # Announce flake8 run
    sys.stdout.write(colored(text="\nStep 3: Checking for pep8 errors.\n\n", color="yellow", attrs=["bold"]))
    print("pep8 errors:")
    print("----------------------------------------------------------------------")

    from subprocess import call
    flake_result = call(["flake8", ".", "--count"])
    if flake_result != 0:
        sys.stderr.write("pep8 errors detected.\n")
        sys.stderr.write(colored(text="\nYOUR CHANGES HAVE INTRODUCED PEP8 ERRORS!\n\n", color="red", attrs=["bold"]))
        sys.exit(flake_result)
    else:
        print("None")

# Announce success
if disable_coverage or disable_pep8:
    sys.stdout.write(colored(text="\nTests completed successfully, but some step(s) were skipped!\n",
                             color="green", attrs=["bold"]))
    sys.stdout.write(colored(text="Don't push without running the skipped step(s).\n",
                             color="red", attrs=["bold"]))
else:
    sys.stdout.write(colored(text="\nTests completed successfully with no errors. Congrats!\n", color="green", attrs=["bold"]))
