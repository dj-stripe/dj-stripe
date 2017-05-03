# -*- coding: utf-8 -*-
"""
.. module:: djstripe.management.commands.djstripe_has_missing_migrations
   :synopsis: dj-stripe - Django command to check for missing migrations.

   Based on: https://gist.github.com/fjsj/3df250b88c0163fd661dfc4d6d67877f

.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

"""

from __future__ import absolute_import, unicode_literals
import sys

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.state import ProjectState
from django.db.utils import OperationalError


class Command(BaseCommand):
    """
    Detect if djstripe missing migration files.
    """
    help = "Detect if any apps have missing migration files"

    def handle(self, *args, **options):
        changed = set()

        self.stdout.write("Checking dj-stripe migrations...")
        for db in settings.DATABASES.keys():
            try:
                executor = MigrationExecutor(connections[db])
            except OperationalError:
                sys.exit("Unable to check migrations: "
                         "cannot connect to database\n")

            autodetector = MigrationAutodetector(
                executor.loader.project_state(),
                ProjectState.from_apps(apps),
            )
            changed.update(
                autodetector.changes(graph=executor.loader.graph).keys())

        if changed and 'djstripe' in changed:
            sys.exit(
                "A migration file is missing, please run the "
                "following to generate one: python makemigrations.py"
            )
        else:
            sys.stdout.write("All migration files present.\n")
