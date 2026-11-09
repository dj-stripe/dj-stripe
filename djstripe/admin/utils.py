"""
Django Administration Utils Module
"""


class ReadOnlyMixin:
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


def _location_kwargs(action_location):
    """Return the keyword arguments that pass `action_location` on to Django.

    Django 6.1 added action locations and calls `ModelAdmin.get_actions()` with
    an `action_location`. Earlier versions have no locations and never pass one,
    so overrides default it to `None` and forward it only when it is given.
    """
    return {} if action_location is None else {"action_location": action_location}


def get_forward_relation_fields_for_model(model):
    """Return an iterable of the field names that are forward relations,
    I.E ManyToManyField, OneToOneField, and ForeignKey.

    Useful for perhaps ensuring the admin is always using raw ID fields for
    newly added forward relation fields.
    """
    return [
        field.name
        for field in model._meta.get_fields()
        # Get only relation fields
        if field.is_relation
        # Exclude auto relation fields, like reverse one to one.
        and not field.auto_created
        # We only want forward relations.
        and any((field.many_to_many, field.one_to_one, field.many_to_one))
    ]
