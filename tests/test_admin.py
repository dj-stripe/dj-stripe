"""
dj-stripe Admin Tests.
"""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase


class TestAdminSite(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )

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
