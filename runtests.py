from argparse import ArgumentParser
import os
import sys

import django
from django.conf import settings

from coverage import coverage
from termcolor import colored

TESTS_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
TESTS_THRESHOLD = 100


def main():
    parser = ArgumentParser(description='Run the dj-stripe Test Suite.')
    parser.add_argument("--skip-utc", action="store_true", help="Skip any tests that require the system timezone to be in UTC.")
    parser.add_argument("--no-coverage", action="store_true", help="Disable checking for 100% code coverage (Not advised).")
    parser.add_argument("--no-pep8", action="store_true", help="Disable checking for pep8 errors (Not advised).")
    args = parser.parse_args()

    run_test_suite(args)


def run_test_suite(args):
    skip_utc = args.skip_utc
    enable_coverage = not args.no_coverage
    enable_pep8 = not args.no_pep8

    if enable_coverage:
        cov = coverage(config_file=True)
        cov.erase()
        cov.start()

    settings.configure(
        DJSTRIPE_TESTS_SKIP_UTC=skip_utc,
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

    # Hack to reset the global argv before nose has a chance to grab it
    # http://stackoverflow.com/a/1718407/1834570
    args = sys.argv[1:]
    sys.argv = sys.argv[0:1]

    from django_nose import NoseTestSuiteRunner

    test_runner = NoseTestSuiteRunner(verbosity=1)
    failures = test_runner.run_tests(["."])

    if failures:
        sys.exit(failures)

    if enable_coverage:
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
        # Announce disabled coverage run
        sys.stdout.write(colored(text="\nStep 2: Generating coverage results [SKIPPED].", color="yellow", attrs=["bold"]))

    if enable_pep8:
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
    else:
        # Announce disabled coverage run
        sys.stdout.write(colored(text="\nStep 3: Checking for pep8 errors [SKIPPED].\n", color="yellow", attrs=["bold"]))

    # Announce success
    if enable_coverage and enable_pep8:
        sys.stdout.write(colored(text="\nTests completed successfully with no errors. Congrats!\n", color="green", attrs=["bold"]))
    else:
        sys.stdout.write(colored(text="\nTests completed successfully, but some step(s) were skipped!\n", color="green", attrs=["bold"]))
        sys.stdout.write(colored(text="Don't push without running the skipped step(s).\n", color="red", attrs=["bold"]))

if __name__ == "__main__":
    main()
