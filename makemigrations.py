"""
Migrations creation/check tool

Based on: https://github.com/pinax/pinax-stripe/blob/master/makemigrations.py
"""

import os
import sys

import django
from django.apps import apps
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError

DEFAULT_SETTINGS = dict(
	DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
	DEBUG=True,
	INSTALLED_APPS=[
		"django.contrib.auth",
		"django.contrib.contenttypes",
		"django.contrib.sessions",
		"django.contrib.sites",
		"jsonfield",
		"djstripe",
	],
	MIDDLEWARE_CLASSES=[
		"django.contrib.sessions.middleware.SessionMiddleware",
		"django.contrib.auth.middleware.AuthenticationMiddleware",
		"django.contrib.messages.middleware.MessageMiddleware",
	],
	ROOT_URLCONF="djstripe.urls",
	SITE_ID=1,
	TIME_ZONE="UTC",
	USE_TZ=True,
)


def check_migrations():
	from django.db.migrations.autodetector import MigrationAutodetector
	from django.db.migrations.executor import MigrationExecutor
	from django.db.migrations.state import ProjectState

	changed = set()

	print("Checking dj-stripe migrations...")
	for db in settings.DATABASES.keys():
		try:
			executor = MigrationExecutor(connections[db])
		except OperationalError as ex:
			sys.exit("Unable to check migrations due to database: {}".format(ex))

		autodetector = MigrationAutodetector(
			executor.loader.project_state(), ProjectState.from_apps(apps)
		)

		changed.update(autodetector.changes(graph=executor.loader.graph).keys())

	if changed and "djstripe" in changed:
		sys.exit(
			"A migration file is missing. Please run "
			"'python makemigrations.py' to generate it."
		)
	else:
		print("All migration files present.")


def run(*args):
	"""
	Check and/or create dj-stripe Django migrations.

	If --check is present in the arguments then migrations are checked only.
	"""
	if not settings.configured:
		settings.configure(**DEFAULT_SETTINGS)

	django.setup()

	parent = os.path.dirname(os.path.abspath(__file__))
	sys.path.insert(0, parent)

	try:
		args = list(args)
		args.pop(args.index("--check"))
		is_check = True
	except ValueError:
		is_check = False

	if is_check:
		check_migrations()
	else:
		django.core.management.call_command("makemigrations", "djstripe", *args)


if __name__ == "__main__":
	run(*sys.argv[1:])
