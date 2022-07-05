from django.core.management.commands.makemigrations import Command  # noqa:F401
from django.db import models

from . import new_deconstruct

models.Field.deconstruct = new_deconstruct
