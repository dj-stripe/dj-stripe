"""
dj-stripe Admin Tests.
"""
from copy import deepcopy
from typing import Sequence

import pytest
import stripe
from django.apps import apps
from django.contrib.admin import helpers, site
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldError
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse
from jsonfield import JSONField
from pytest_django.asserts import assertQuerysetEqual

from djstripe import models, utils
from djstripe.admin import admin as djstripe_admin
from djstripe.admin.forms import CustomActionForm
from djstripe.models.account import Account
from tests import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_INVOICE,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PLAN,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_SCHEDULE,
)

from .fields.models import CustomActionModel

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "output,input",
    [
        (
            ["event", "stripe_trigger_account", "webhook_endpoint"],
            models.WebhookEventTrigger,
        ),
        (
            [
                "djstripe_owner_account",
                "customer",
                "default_payment_method",
                "default_source",
                "latest_invoice",
                "pending_setup_intent",
                "plan",
                "schedule",
                "default_tax_rates",
            ],
            models.Subscription,
        ),
        (
            [
                "djstripe_owner_account",
                "default_source",
                "coupon",
                "default_payment_method",
                "subscriber",
            ],
            models.Customer,
        ),
    ],
)
def test_get_forward_relation_fields_for_model(output, input):
    assert output == djstripe_admin.get_forward_relation_fields_for_model(input)


class TestAdminRegisteredModelsChildrenOfStripeModel(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@djstripe.com", password="xxx"
        )
        self.factory = RequestFactory()
        # the 4 models that do not inherit from StripeModel and hence
        # do not inherit from StripeModelAdmin
        self.ignore_models = [
            "WebhookEventTrigger",
            "WebhookEndpoint",
            "IdempotencyKey",
            "APIKey",
        ]

    def test_get_list_display_links(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard changelist_view url
                url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                # add the admin user to the mocked request
                request = self.factory.get(url)
                request.user = self.admin

                response = model_admin.changelist_view(request)
                list_display = model_admin.get_changelist_instance(request).list_display

                # get_changelist_instance to get an instance of the ChangelistView for logged in admin user
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    list(response.context_data["cl"].list_display_links),
                    list(
                        model_admin.get_changelist_instance(request).list_display_links
                    ),
                )

                # ensure all the fields in list_display_links are valid
                for field in model_admin.get_list_display_links(request, list_display):
                    model_admin.get_changelist_instance(request).get_ordering_field(
                        field
                    )

    def test_get_list_display(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard changelist_view url
                url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                # add the admin user to the mocked request
                request = self.factory.get(url)
                request.user = self.admin

                response = model_admin.changelist_view(request)

                # get_changelist_instance to get an instance of the ChangelistView for logged in admin user
                list_display = model_admin.get_changelist_instance(request).list_display
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    list(response.context_data["cl"].list_display),
                    list(list_display),
                )

                # ensure all the fields in list_display are valid
                for field in model_admin.get_list_display(request):
                    model_admin.get_changelist_instance(request).get_ordering_field(
                        field
                    )

                # for models inheriting from StripeModelAdmin verify:
                if model.__name__ not in self.ignore_models:
                    self.assertTrue(
                        all(
                            [
                                1
                                for i in [
                                    "__str__",
                                    "id",
                                    "djstripe_owner_account",
                                    "created",
                                    "livemode",
                                ]
                                if i in list_display
                            ]
                        )
                    )

    def test_get_list_filter(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard changelist_view url
                url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                # add the admin user to the mocked request
                request = self.factory.get(url)
                request.user = self.admin

                response = model_admin.changelist_view(request)

                # get_changelist_instance to get an instance of the ChangelistView for logged in admin user
                list_filter = model_admin.get_changelist_instance(request).list_filter
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    list(response.context_data["cl"].list_filter),
                    list(list_filter),
                )

                # ensure all the filters get formed correctly
                chl = model_admin.get_changelist_instance(request)
                chl.get_filters(request)
                chl.get_queryset(request)

                # for models inheriting from StripeModelAdmin verify:
                if model.__name__ not in self.ignore_models:
                    self.assertTrue(
                        all([1 for i in ["created", "livemode"] if i in list_filter])
                    )

    def test_get_readonly_fields(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard changelist_view url
                url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                # add the admin user to the mocked request
                request = self.factory.get(url)
                request.user = self.admin

                response = model_admin.changelist_view(request)

                # get_changelist_instance to get an instance of the ChangelistView for logged in admin user
                readonly_fields = model_admin.get_changelist_instance(
                    request
                ).model_admin.readonly_fields
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context_data["cl"].model_admin.readonly_fields,
                    readonly_fields,
                )

                # ensure all the fields in readonly_fields are valid
                for field in model_admin.get_readonly_fields(request):
                    # ensure the given field is on model, or model_admin or modelform
                    model_admin.get_changelist_instance(request).get_ordering_field(
                        field
                    )

                # for models inheriting from StripeModelAdmin verify:
                if model.__name__ not in self.ignore_models:
                    self.assertTrue(
                        all(
                            [
                                1
                                for i in ["created", "djstripe_owner_account", "id"]
                                if i in readonly_fields
                            ]
                        )
                    )

    def test_get_list_select_related(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard changelist_view url
                url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                # add the admin user to the mocked request
                request = self.factory.get(url)
                request.user = self.admin

                response = model_admin.changelist_view(request)

                # get_changelist_instance to get an instance of the ChangelistView for logged in admin user
                list_select_related = model_admin.get_changelist_instance(
                    request
                ).list_select_related
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context_data["cl"].list_select_related,
                    list_select_related,
                )

                # ensure all the fields in list_select_related are valid
                list_select_related_fields = model_admin.get_list_select_related(
                    request
                )
                if isinstance(list_select_related_fields, Sequence):
                    # need to force the returned queryset to get evaluated
                    list(model.objects.select_related(*list_select_related_fields))

    # todo complete after djstripe has integrated ModelFactory
    # def test_get_fieldsets_change(self):
    #     pass

    def test_get_fieldsets_add(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard add url
                add_url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_add"
                )

                # add the admin user to the mocked request
                request = self.factory.get(add_url)
                request.user = self.admin

                # skip model if model doesn't have "has_add_permission"
                if not model_admin.has_add_permission(request):
                    continue

                response = model_admin.add_view(request)

                fieldsets = model_admin.get_fieldsets(request)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context_data["adminform"].fieldsets,
                    [*fieldsets],
                )

                # for models inheriting from StripeModelAdmin verify:
                if model.__name__ not in self.ignore_models:
                    self.assertTrue(
                        all(
                            [
                                1
                                for i in [
                                    "created",
                                    "livemode",
                                    "djstripe_owner_account",
                                    "id",
                                ]
                                if i in fieldsets
                            ]
                        )
                    )

    # todo complete after djstripe has integrated ModelFactory
    # def test_get_fields_change(self):
    #     pass

    def test_get_fields_add(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard add url
                add_url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_add"
                )

                # add the admin user to the mocked request
                request = self.factory.get(add_url)
                request.user = self.admin

                # skip model if model doesn't have "has_add_permission"
                if not model_admin.has_add_permission(request):
                    continue

                response = model_admin.add_view(request)

                fields = model_admin.get_fields(request)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context_data["adminform"].model_admin.get_fields(request),
                    list(fields),
                )

                # ensure all the fields in model_admin are valid
                for field in model_admin.get_fields(request):
                    # as these fields are form field and not modelform fields
                    if model_admin.model is models.WebhookEndpoint and field in (
                        "base_url",
                        "enabled",
                        "connect",
                    ):
                        continue
                    model_admin.get_changelist_instance(request).get_ordering_field(
                        field
                    )

    def test_get_search_fields(self):
        """
        Ensure all fields in model_admin.get_search_fields exist on the model or the related model
        """

        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard changelist_view url and make a sample query to trigger search
                url = (
                    reverse(
                        f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                    )
                    + "?q=bar"
                )

                # add the admin user to the mocked request
                request = self.factory.get(url)
                request.user = self.admin

                response = model_admin.changelist_view(request)

                search_fields = model_admin.get_changelist_instance(
                    request
                ).search_fields
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context_data["cl"].search_fields,
                    search_fields,
                )

                try:
                    # ensure all the fields in search_fields are valid
                    # need to force the returned queryset to get evaluated
                    list(model.objects.select_related(*search_fields))
                except FieldError as error:
                    if "Non-relational field given in select_related" not in str(error):
                        self.fail(error)

                # for models inheriting from StripeModelAdmin verify:
                if model.__name__ not in self.ignore_models:
                    self.assertTrue("id" in search_fields)

    def test_get_actions(self):

        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)

                # get the standard changelist_view url
                url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                # add the admin user to the mocked request
                request = self.factory.get(url)
                request.user = self.admin

                actions = model_admin.get_actions(request)

                # sub-classes of StripeModel
                if model.__name__ not in self.ignore_models:
                    if model.__name__ == "UsageRecordSummary":
                        assert "_resync_instances" not in actions
                        assert "_sync_all_instances" in actions
                    elif model.__name__ == "Subscription":
                        assert "_resync_instances" in actions
                        assert "_sync_all_instances" in actions
                        assert "_cancel" in actions
                    elif model.__name__ in ("Mandate", "UsageRecord"):
                        assert "_resync_instances" in actions
                        assert "_sync_all_instances" not in actions
                    else:
                        assert "_resync_instances" in actions
                        assert "_sync_all_instances" in actions

                # not sub-classes of StripeModel
                else:
                    if model.__name__ == "WebhookEndpoint":
                        assert "delete_selected" not in actions
                        assert "_resync_instances" in actions
                        assert "_sync_all_instances" in actions
                    else:
                        assert "_resync_instances" not in actions
                        assert "_sync_all_instances" not in actions


class TestAdminRegisteredModelsNotChildrenOfStripeModel(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@djstripe.com", password="xxx"
        )
        self.factory = RequestFactory()

    def test_get_list_display_links(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard changelist_view url
                url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                # add the admin user to the mocked request
                request = self.factory.get(url)
                request.user = self.admin

                response = model_admin.changelist_view(request)
                list_display = model_admin.get_changelist_instance(request).list_display

                # get_changelist_instance to get an instance of the ChangelistView for logged in admin user
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    list(response.context_data["cl"].list_display_links),
                    list(
                        model_admin.get_changelist_instance(request).list_display_links
                    ),
                )

                # ensure all the fields in list_display_links are valid
                for field in model_admin.get_list_display_links(request, list_display):
                    model_admin.get_changelist_instance(request).get_ordering_field(
                        field
                    )

    def test_get_list_display(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard changelist_view url
                url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                # add the admin user to the mocked request
                request = self.factory.get(url)
                request.user = self.admin

                response = model_admin.changelist_view(request)

                # get_changelist_instance to get an instance of the ChangelistView for logged in admin user
                list_display = model_admin.get_changelist_instance(request).list_display
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    list(response.context_data["cl"].list_display),
                    list(list_display),
                )

                # ensure all the fields in list_display are valid
                for field in model_admin.get_list_display(request):
                    model_admin.get_changelist_instance(request).get_ordering_field(
                        field
                    )

                self.assertTrue(
                    all(
                        [
                            1
                            for i in [
                                "__str__",
                                "id",
                                "djstripe_owner_account",
                                "created",
                                "livemode",
                            ]
                            if i in list_display
                        ]
                    )
                )

    def test_get_list_filter(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard changelist_view url
                url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                # add the admin user to the mocked request
                request = self.factory.get(url)
                request.user = self.admin

                response = model_admin.changelist_view(request)

                # get_changelist_instance to get an instance of the ChangelistView for logged in admin user
                list_filter = model_admin.get_changelist_instance(request).list_filter
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    list(response.context_data["cl"].list_filter),
                    list(list_filter),
                )

                # ensure all the filters get formed correctly
                chl = model_admin.get_changelist_instance(request)
                chl.get_filters(request)
                chl.get_queryset(request)

                self.assertTrue(
                    all([1 for i in ["created", "livemode"] if i in list_filter])
                )

    def test_get_readonly_fields(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard changelist_view url
                url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                # add the admin user to the mocked request
                request = self.factory.get(url)
                request.user = self.admin

                response = model_admin.changelist_view(request)

                # get_changelist_instance to get an instance of the ChangelistView for logged in admin user
                readonly_fields = model_admin.get_changelist_instance(
                    request
                ).model_admin.readonly_fields
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context_data["cl"].model_admin.readonly_fields,
                    readonly_fields,
                )

                # ensure all the fields in readonly_fields are valid
                for field in model_admin.get_readonly_fields(request):
                    # ensure the given field is on model, or model_admin or modelform
                    model_admin.get_changelist_instance(request).get_ordering_field(
                        field
                    )

                self.assertTrue(
                    all(
                        [
                            1
                            for i in ["created", "djstripe_owner_account", "id"]
                            if i in readonly_fields
                        ]
                    )
                )

    def test_get_list_select_related(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard changelist_view url
                url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                # add the admin user to the mocked request
                request = self.factory.get(url)
                request.user = self.admin

                response = model_admin.changelist_view(request)

                # get_changelist_instance to get an instance of the ChangelistView for logged in admin user
                list_select_related = model_admin.get_changelist_instance(
                    request
                ).list_select_related
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context_data["cl"].list_select_related,
                    list_select_related,
                )

                # ensure all the fields in list_select_related are valid
                list_select_related_fields = model_admin.get_list_select_related(
                    request
                )
                if isinstance(list_select_related_fields, Sequence):
                    # need to force the returned queryset to get evaluated
                    list(model.objects.select_related(*list_select_related_fields))

    # todo complete after djstripe has integrated ModelFactory
    # def test_get_fieldsets_change(self):
    #     pass

    def test_get_fieldsets_add(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard add url
                add_url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_add"
                )

                # add the admin user to the mocked request
                request = self.factory.get(add_url)
                request.user = self.admin

                # skip model if model doesn't have "has_add_permission"
                if not model_admin.has_add_permission(request):
                    continue

                response = model_admin.add_view(request)

                fieldsets = model_admin.get_fieldsets(request)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context_data["adminform"].fieldsets,
                    [*fieldsets],
                )

                self.assertTrue(
                    all(
                        [
                            1
                            for i in [
                                "created",
                                "livemode",
                                "djstripe_owner_account",
                                "id",
                            ]
                            if i in fieldsets
                        ]
                    )
                )

    # todo complete after djstripe has integrated ModelFactory
    # def test_get_fields_change(self):
    #     pass

    def test_get_fields_add(self):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard add url
                add_url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_add"
                )

                # add the admin user to the mocked request
                request = self.factory.get(add_url)
                request.user = self.admin

                # skip model if model doesn't have "has_add_permission"
                if not model_admin.has_add_permission(request):
                    continue

                response = model_admin.add_view(request)

                fields = model_admin.get_fields(request)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context_data["adminform"].model_admin.get_fields(request),
                    list(fields),
                )

                # ensure all the fields in model_admin are valid
                for field in model_admin.get_fields(request):
                    # as these fields are form field and not modelform fields
                    if model_admin.model is models.WebhookEndpoint and field in (
                        "base_url",
                        "enabled",
                        "connect",
                    ):
                        continue
                    model_admin.get_changelist_instance(request).get_ordering_field(
                        field
                    )

    def test_get_search_fields(self):
        """
        Ensure all fields in model_admin.get_search_fields exist on the model or the related model
        """

        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)
                # get the standard changelist_view url and make a sample query to trigger search
                url = (
                    reverse(
                        f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                    )
                    + "?q=bar"
                )

                # add the admin user to the mocked request
                request = self.factory.get(url)
                request.user = self.admin

                response = model_admin.changelist_view(request)

                search_fields = model_admin.get_changelist_instance(
                    request
                ).search_fields
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context_data["cl"].search_fields,
                    search_fields,
                )

                try:
                    # ensure all the fields in search_fields are valid
                    # need to force the returned queryset to get evaluated
                    list(model.objects.select_related(*search_fields))
                except FieldError as error:
                    if "Non-relational field given in select_related" not in str(error):
                        self.fail(error)


class TestAdminInlineModels(TestCase):
    def test_readonly_fields_exist(self):
        """
        Ensure all fields in BaseModelAdmin.readonly_fields exist on the model
        """

        for model, model_admin in site._registry.items():
            for inline_admin in model_admin.inlines:
                fields = getattr(inline_admin, "readonly_fields", [])
                try:
                    # need to force the returned queryset to get evaluated
                    list(inline_admin.model.objects.select_related(*fields))
                except FieldError as error:
                    if "Non-relational field given in select_related" not in str(error):
                        self.fail(error)


class TestAdminSite(TestCase):
    def setUp(self):
        self.empty_value = "-empty-"

    def test_search_fields(self):
        """
        Search for errors like this:
        Bad search field <customer__user__username> for Customer model.
        """

        for _model, model_admin in site._registry.items():
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

    def test_search_fields_exist(self):
        """
        Ensure all fields in model_admin.search_fields exist on the model or the related model
        """

        for model, model_admin in site._registry.items():
            fields = getattr(model_admin, "search_fields", [])
            try:
                # need to force the returned queryset to get evaluated
                list(model.objects.select_related(*fields))
            except FieldError as error:
                if "Non-relational field given in select_related" not in str(error):
                    self.fail(error)

    def test_list_select_related_fields_exist(self):
        """
        Ensure all fields in model_admin.list_select_related exist on the model or the related model
        """

        for model, model_admin in site._registry.items():
            fields = getattr(model_admin, "list_select_related", False)
            if isinstance(fields, Sequence):
                try:
                    # need to force the returned queryset to get evaluated
                    list(model.objects.select_related(*fields))
                except FieldError as error:
                    self.fail(error)

    def test_custom_display_for_JSONfield(self):
        json_tests = [
            ({"a": {"b": None}}, '{"a": {"b": null}}'),
            (["a", False], '["a", false]'),
            ("a", '"a"'),
            ({("a", "b"): "c"}, "{('a', 'b'): 'c'}"),  # Invalid JSON.
        ]
        for value, display_value in json_tests:
            with self.subTest(value=value):
                self.assertEqual(
                    djstripe_admin.custom_display_for_JSONfield(
                        value, JSONField(), self.empty_value
                    ),
                    display_value,
                )


class TestCustomActionMixin:
    # the 4 models that do not inherit from StripeModel and hence
    # do not inherit from StripeModelAdmin
    ignore_models = [
        "WebhookEventTrigger",
        "WebhookEndpoint",
        "IdempotencyKey",
        "APIKey",
    ]

    @pytest.mark.parametrize(
        "action_name", ["_sync_all_instances", "_resync_instances"]
    )
    @pytest.mark.parametrize("djstripe_owner_account_exists", [False, True])
    def test_get_admin_action_context(
        self, djstripe_owner_account_exists, action_name, monkeypatch
    ):
        # monkeypatch utils.get_model
        def mock_get_model(*args, **kwargs):
            return model

        monkeypatch.setattr(utils, "get_model", mock_get_model)

        model = CustomActionModel

        # create instance to be used in the Django Admin Action
        instance = model.objects.create(id="test")

        if djstripe_owner_account_exists:
            account_instance = Account.objects.first()
            instance.djstripe_owner_account = account_instance
            instance.save()

        queryset = model.objects.all()
        model_admin = site._registry.get(model)

        context = model_admin.get_admin_action_context(
            queryset, action_name, CustomActionForm
        )

        assert context.get("queryset") == queryset
        assert context.get("action_name") == action_name
        assert context.get("model_name") == "customactionmodel"
        assert context.get("changelist_url") == "/admin/fields/customactionmodel/"
        assert context.get("ACTION_CHECKBOX_NAME") == helpers.ACTION_CHECKBOX_NAME

        if action_name == "_sync_all_instances":
            assert context.get("info") == []
            assertQuerysetEqual(
                context.get("form").initial.get(helpers.ACTION_CHECKBOX_NAME),
                ["_sync_all_instances"],
            )
            assert context.get("form").fields.get(
                helpers.ACTION_CHECKBOX_NAME
            ).choices == [("_sync_all_instances", "_sync_all_instances")]
        else:
            assert context.get("info") == [
                f'Custom action model: <a href="/admin/fields/customactionmodel/{instance.pk}/change/">&lt;id=test&gt;</a>'
            ]

            assertQuerysetEqual(
                context.get("form").initial.get(helpers.ACTION_CHECKBOX_NAME),
                queryset.values_list("pk", flat=True),
            )
            assert context.get("form").fields.get(
                helpers.ACTION_CHECKBOX_NAME
            ).choices == list(
                zip(
                    queryset.values_list("pk", flat=True),
                    queryset.values_list("pk", flat=True),
                )
            )

    def test_get_actions(self, admin_user):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys():
                model_admin = site._registry.get(model)

                # get the standard changelist_view url
                url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                # add the admin user to the mocked request
                request = RequestFactory().get(url)
                request.user = admin_user

                actions = model_admin.get_actions(request)

                # sub-classes of StripeModel
                if model.__name__ not in self.ignore_models:

                    if getattr(model.stripe_class, "retrieve", None):
                        # assert "_resync_instances" action is present
                        assert "_resync_instances" in actions
                    else:
                        # assert "_resync_instances" action is not present
                        assert "_resync_instances" not in actions

    @pytest.mark.parametrize("fake_selected_pks", [None, [1, 2]])
    def test_changelist_view(self, admin_client, fake_selected_pks):

        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys() and (
                model.__name__ == "WebhookEndpoint"
                or model.__name__ not in self.ignore_models
            ):

                # get the standard changelist_view url
                change_url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                data = {"action": "_sync_all_instances"}

                if fake_selected_pks is not None:
                    # add key helpers.ACTION_CHECKBOX_NAME when it is not None
                    data[helpers.ACTION_CHECKBOX_NAME] = fake_selected_pks

                # get the response. This will invoke the changelist_view
                response = admin_client.post(change_url, data=data, follow=True)

                assert response.status_code == 200

    @pytest.mark.parametrize("djstripe_owner_account_exists", [False, True])
    def test__resync_instances(
        self, djstripe_owner_account_exists, admin_client, monkeypatch
    ):
        model = CustomActionModel
        model_admin = site._registry.get(model)

        # monkeypatch utils.get_model
        def mock_get_model(*args, **kwargs):
            return model

        # monkeypatch modeladmin.get_admin_action_context
        def mock_get_admin_action_context(*args, **kwargs):
            return {
                "action_name": "_resync_instances",
                "model_name": "customactionmodel",
            }

        monkeypatch.setattr(
            model_admin, "get_admin_action_context", mock_get_admin_action_context
        )
        monkeypatch.setattr(utils, "get_model", mock_get_model)

        # create instance to be used in the Django Admin Action
        instance = model.objects.create(id="test")

        if djstripe_owner_account_exists:
            account_instance = Account.objects.first()
            instance.djstripe_owner_account = account_instance
            instance.save()

        data = {
            "action": "_resync_instances",
            helpers.ACTION_CHECKBOX_NAME: [instance.pk],
        }

        # get the standard changelist_view url
        change_url = reverse(
            f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
        )

        response = admin_client.post(change_url, data)

        # assert user got 200 status code
        assert response.status_code == 200

    @pytest.mark.parametrize("fake_selected_pks", [None, [1, 2]])
    def test__sync_all_instances(self, admin_client, fake_selected_pks):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if (
                model in site._registry.keys()
                and model.__name__ not in ("Mandate", "UsageRecord")
                and (
                    model.__name__ == "WebhookEndpoint"
                    or model.__name__ not in self.ignore_models
                )
            ):

                # get the standard changelist_view url
                change_url = reverse(
                    f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
                )

                data = {"action": "_sync_all_instances"}

                if fake_selected_pks is not None:
                    data[helpers.ACTION_CHECKBOX_NAME] = fake_selected_pks

                response = admin_client.post(change_url, data)

                # assert user got 200 status code
                assert response.status_code == 200


class TestSubscriptionAdminCustomAction:
    def test__cancel_subscription_instances(
        self,
        admin_client,
        monkeypatch,
    ):
        def mock_invoice_get(*args, **kwargs):
            return FAKE_INVOICE

        def mock_customer_get(*args, **kwargs):
            return FAKE_CUSTOMER

        def mock_charge_get(*args, **kwargs):
            return FAKE_CHARGE

        def mock_payment_method_get(*args, **kwargs):
            return FAKE_CARD_AS_PAYMENT_METHOD

        def mock_payment_intent_get(*args, **kwargs):
            return FAKE_PAYMENT_INTENT_I

        def mock_subscription_get(*args, **kwargs):
            return FAKE_SUBSCRIPTION

        def mock_balance_transaction_get(*args, **kwargs):
            return FAKE_BALANCE_TRANSACTION

        def mock_product_get(*args, **kwargs):
            return FAKE_PRODUCT

        def mock_plan_get(*args, **kwargs):
            return FAKE_PLAN

        # monkeypatch stripe retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Invoice, "retrieve", mock_invoice_get)
        monkeypatch.setattr(stripe.Customer, "retrieve", mock_customer_get)
        monkeypatch.setattr(
            stripe.BalanceTransaction, "retrieve", mock_balance_transaction_get
        )
        monkeypatch.setattr(stripe.Subscription, "retrieve", mock_subscription_get)
        monkeypatch.setattr(stripe.Charge, "retrieve", mock_charge_get)
        monkeypatch.setattr(stripe.PaymentMethod, "retrieve", mock_payment_method_get)
        monkeypatch.setattr(stripe.PaymentIntent, "retrieve", mock_payment_intent_get)
        monkeypatch.setattr(stripe.Product, "retrieve", mock_product_get)
        monkeypatch.setattr(stripe.Plan, "retrieve", mock_plan_get)

        # Create Latest Invoice
        models.Invoice.sync_from_stripe_data(FAKE_INVOICE)

        model = models.Subscription
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        instance = model.sync_from_stripe_data(subscription_fake)

        # get the standard changelist_view url
        change_url = reverse(
            f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
        )

        data = {"action": "_cancel", helpers.ACTION_CHECKBOX_NAME: [instance.pk]}

        response = admin_client.post(change_url, data)

        # assert user got 200 status code
        assert response.status_code == 200


class TestSubscriptionScheduleAdminCustomAction:
    def test__release_subscription_schedule(
        self,
        admin_client,
        monkeypatch,
    ):
        def mock_balance_transaction_get(*args, **kwargs):
            return FAKE_BALANCE_TRANSACTION

        def mock_subscription_get(*args, **kwargs):
            return FAKE_SUBSCRIPTION

        def mock_charge_get(*args, **kwargs):
            return FAKE_CHARGE

        def mock_payment_method_get(*args, **kwargs):
            return FAKE_CARD_AS_PAYMENT_METHOD

        def mock_payment_intent_get(*args, **kwargs):
            return FAKE_PAYMENT_INTENT_I

        def mock_product_get(*args, **kwargs):
            return FAKE_PRODUCT

        def mock_invoice_get(*args, **kwargs):
            return FAKE_INVOICE

        def mock_customer_get(*args, **kwargs):
            return FAKE_CUSTOMER

        def mock_plan_get(*args, **kwargs):
            return FAKE_PLAN

        # monkeypatch stripe retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(
            stripe.BalanceTransaction, "retrieve", mock_balance_transaction_get
        )
        monkeypatch.setattr(stripe.Subscription, "retrieve", mock_subscription_get)
        monkeypatch.setattr(stripe.Charge, "retrieve", mock_charge_get)

        monkeypatch.setattr(stripe.PaymentMethod, "retrieve", mock_payment_method_get)
        monkeypatch.setattr(stripe.PaymentIntent, "retrieve", mock_payment_intent_get)
        monkeypatch.setattr(stripe.Product, "retrieve", mock_product_get)

        monkeypatch.setattr(stripe.Invoice, "retrieve", mock_invoice_get)
        monkeypatch.setattr(stripe.Customer, "retrieve", mock_customer_get)

        monkeypatch.setattr(stripe.Plan, "retrieve", mock_plan_get)

        # create latest invoice
        models.Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        model = models.SubscriptionSchedule
        subscription_schedule_fake = deepcopy(FAKE_SUBSCRIPTION_SCHEDULE)
        instance = model.sync_from_stripe_data(subscription_schedule_fake)

        # get the standard changelist_view url
        change_url = reverse(
            f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
        )

        data = {
            "action": "_release_subscription_schedule",
            helpers.ACTION_CHECKBOX_NAME: [instance.pk],
        }

        response = admin_client.post(change_url, data)

        # assert user got 200 status code
        assert response.status_code == 200

    def test__cancel_subscription_schedule(
        self,
        admin_client,
        monkeypatch,
    ):
        def mock_balance_transaction_get(*args, **kwargs):
            return FAKE_BALANCE_TRANSACTION

        def mock_subscription_get(*args, **kwargs):
            return FAKE_SUBSCRIPTION

        def mock_charge_get(*args, **kwargs):
            return FAKE_CHARGE

        def mock_payment_method_get(*args, **kwargs):
            return FAKE_CARD_AS_PAYMENT_METHOD

        def mock_payment_intent_get(*args, **kwargs):
            return FAKE_PAYMENT_INTENT_I

        def mock_product_get(*args, **kwargs):
            return FAKE_PRODUCT

        def mock_invoice_get(*args, **kwargs):
            return FAKE_INVOICE

        def mock_customer_get(*args, **kwargs):
            return FAKE_CUSTOMER

        def mock_plan_get(*args, **kwargs):
            return FAKE_PLAN

        # monkeypatch stripe retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(
            stripe.BalanceTransaction, "retrieve", mock_balance_transaction_get
        )
        monkeypatch.setattr(stripe.Subscription, "retrieve", mock_subscription_get)
        monkeypatch.setattr(stripe.Charge, "retrieve", mock_charge_get)

        monkeypatch.setattr(stripe.PaymentMethod, "retrieve", mock_payment_method_get)
        monkeypatch.setattr(stripe.PaymentIntent, "retrieve", mock_payment_intent_get)
        monkeypatch.setattr(stripe.Product, "retrieve", mock_product_get)

        monkeypatch.setattr(stripe.Invoice, "retrieve", mock_invoice_get)
        monkeypatch.setattr(stripe.Customer, "retrieve", mock_customer_get)

        monkeypatch.setattr(stripe.Plan, "retrieve", mock_plan_get)

        # create latest invoice
        models.Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        model = models.SubscriptionSchedule
        subscription_schedule_fake = deepcopy(FAKE_SUBSCRIPTION_SCHEDULE)
        instance = model.sync_from_stripe_data(subscription_schedule_fake)

        # get the standard changelist_view url
        change_url = reverse(
            f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
        )

        data = {
            "action": "_cancel_subscription_schedule",
            helpers.ACTION_CHECKBOX_NAME: [instance.pk],
        }

        response = admin_client.post(change_url, data)

        # assert user got 200 status code
        assert response.status_code == 200
