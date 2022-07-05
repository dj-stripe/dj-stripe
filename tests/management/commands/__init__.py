from django.db import models

original_deconstruct = models.Field.deconstruct

IGNORED_ATTRS = [
    "verbose_name",
    "help_text",
    "choices",
    "get_latest_by",
    "ordering",
]


def new_deconstruct(self):
    """Remove field attributes that have nothing to
    do with the database. Otherwise unencessary migrations are generated."""

    # we use original_deconstruct to reference the models.Field baseclass.
    name, path, args, kwargs = original_deconstruct(self)
    for attr in IGNORED_ATTRS:
        kwargs.pop(attr, None)
    return name, path, args, kwargs
