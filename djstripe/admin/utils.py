"""
Django Administration Utils Module
"""
import json

from django.contrib.admin.utils import display_for_field, display_for_value
from jsonfield import JSONField


class ReadOnlyMixin:
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


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


def custom_display_for_JSONfield(value, field, empty_value_display):
    """
    Overriding display_for_field to correctly render JSONField READonly fields
    in django-admin. Relevant when DJSTRIPE_USE_NATIVE_JSONFIELD is False
    Note: This does not handle invalid JSON. That should be handled by the JSONField itself
    """
    # we manually JSON serialise in case field is from jsonfield module
    if isinstance(field, JSONField) and value:
        try:
            return json.dumps(value)
        except TypeError:
            return display_for_value(value, empty_value_display)
    return display_for_field(value, field, empty_value_display)
