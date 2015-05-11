"""
.. module:: dj-stripe.tests.test_admin
   :synopsis: dj-stripe Admin Tests.

.. moduleauthor:: Oleksandr (@nanvel)

"""

import six

from django.contrib import admin
from django.test import TestCase


class TestAdminSite(TestCase):

    def test_search_fields(self):
        """
        Search for errors like this:
        Bad search field <customer__user__username> for Customer model.
        """

        for model, model_admin in six.iteritems(admin.site._registry):
            for search_field in getattr(model_admin, 'search_fields', []):
                model_name = model_admin.model.__name__
                self.assertFalse(search_field.startswith('{table_name}__'.format(
                    table_name=model_name.lower())),
                    'Bad search field <{search_field}> for {model_name} model.'.format(
                        search_field=search_field, model_name=model_name))
