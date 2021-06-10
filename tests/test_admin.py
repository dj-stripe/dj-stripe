"""
dj-stripe Admin Tests.
"""
from django.contrib import admin
from django.test import TestCase
from jsonfield import JSONField

from djstripe.admin import custom_display_for_JSONfield


class TestAdminSite(TestCase):
    def setUp(self):
        self.empty_value = "-empty-"

    def test_search_fields(self):
        """
        Search for errors like this:
        Bad search field <customer__user__username> for Customer model.
        """

        for _model, model_admin in admin.site._registry.items():
            for search_field in getattr(model_admin, "search_fields", []):
                model_name = model_admin.model.__name__
                self.assertFalse(
                    search_field.startswith(
                        "{table_name}__".format(table_name=model_name.lower())
                    ),
                    "Bad search field <{search_field}> for {model_name} model.".format(
                        search_field=search_field, model_name=model_name
                    ),
                )

    def test_json_display_for_field(self):
        json_tests = [
            ({"a": {"b": None}}, '{"a": {"b": null}}'),
            (["a", False], '["a", false]'),
            ("a", '"a"'),
            ({("a", "b"): "c"}, "{('a', 'b'): 'c'}"),  # Invalid JSON.
        ]
        for value, display_value in json_tests:
            with self.subTest(value=value):
                self.assertEqual(
                    custom_display_for_JSONfield(value, JSONField(), self.empty_value),
                    display_value,
                )
