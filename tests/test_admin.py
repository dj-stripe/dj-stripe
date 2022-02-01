"""
dj-stripe Admin Tests.
"""
from copy import deepcopy
from typing import Sequence
from unittest.mock import patch

import pytest
from django.apps import apps
from django.contrib import messages
from django.contrib.admin import helpers, site
from django.contrib.auth import get_user_model
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import FieldError
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse
from jsonfield import JSONField
from stripe.error import InvalidRequestError

from djstripe import admin as djstripe_admin
from djstripe import models
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
)

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


class TestAdminCustomActions(TestCase):
    kwargs_called_with = {}

    # to get around Session/MessageMiddleware Deprecation Warnings
    def dummy_get_response(self, request):
        return None

    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", autospec=True, return_value=deepcopy(FAKE_INVOICE)
    )
    def setUp(
        self,
        invoice_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        self.admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@djstripe.com", password="xxx"
        )
        self.factory = RequestFactory()

        self.customer = FAKE_CUSTOMER.create_for_user(self.admin)

        # create latest invoice
        models.Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test__cancel_subcriptions(
        self,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):

        # create instance to be used in the Django Admin Action
        subscription = models.Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)

        model = models.Subscription
        model_admin = site._registry.get(model)

        data = {
            "action": "_cancel",
            helpers.ACTION_CHECKBOX_NAME: [subscription.pk],
        }

        # get the standard changelist_view url
        change_url = reverse(
            f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
        )

        # add the admin user to the mocked request and disable CSRF checks
        request = self.factory.post(change_url, data=data, follow=True)
        request.user = self.admin
        request._dont_enforce_csrf_checks = True

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        # get the _cancel custom Django Admin Action
        action_fn = model_admin.get_actions(request)[data.get("action")][0]

        with patch.object(
            subscription, "_api_delete", return_value=FAKE_SUBSCRIPTION
        ) as patched__api_delete:
            # invoke the _cancel action
            action_fn(model_admin, request, [subscription])

            messages_sent_dictionary = {
                m.message: m.level_tag for m in messages.get_messages(request)
            }

            # assert correct success message was emmitted
            assert (
                messages_sent_dictionary.get(f"Successfully Canceled: {subscription}")
                == "success"
            )

        patched__api_delete.assert_called_once_with()

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test__cancel_subcriptions_handled_invalid_stripe_request_error_raised(
        self,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):

        # create instance to be used in the Django Admin Action
        subscription = models.Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)

        model = models.Subscription
        model_admin = site._registry.get(model)

        data = {
            "action": "_cancel",
            helpers.ACTION_CHECKBOX_NAME: [subscription.pk],
        }

        # monkeypatch instance.api_retrieve
        def mock_instance_api_retrieve(*args, **kwargs):
            raise InvalidRequestError("No such subscription:", {})

        # get the standard changelist_view url
        change_url = reverse(
            f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
        )

        # add the admin user to the mocked request and disable CSRF checks
        request = self.factory.post(change_url, data=data, follow=True)
        request.user = self.admin
        request._dont_enforce_csrf_checks = True

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        # get the _cancel custom Django Admin Action
        action_fn = model_admin.get_actions(request)[data.get("action")][0]

        with patch.object(
            subscription, "api_retrieve", return_value=FAKE_SUBSCRIPTION
        ) as patched_api_retrieve:
            with patch.object(
                subscription, "_api_delete", side_effect=mock_instance_api_retrieve
            ) as patched__api_delete:

                # invoke the _cancel action
                action_fn(model_admin, request, [subscription])

                messages_sent_dictionary = {
                    m.message: m.level_tag for m in messages.get_messages(request)
                }

                # assert correct success message was emmitted
                assert (
                    messages_sent_dictionary.get(
                        f"Successfully Canceled: {subscription}"
                    )
                    == "success"
                )

            patched__api_delete.assert_called_once_with()
        patched_api_retrieve.assert_called_once_with()

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test__cancel_subcriptions_unhandled_invalid_stripe_request_error_raised(
        self,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):

        # create instance to be used in the Django Admin Action
        subscription = models.Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)

        model = models.Subscription
        model_admin = site._registry.get(model)

        data = {
            "action": "_cancel",
            helpers.ACTION_CHECKBOX_NAME: [subscription.pk],
        }

        # monkeypatch instance.api_retrieve
        def mock_instance_api_retrieve(*args, **kwargs):
            raise InvalidRequestError("some random error message:", {})

        # get the standard changelist_view url
        change_url = reverse(
            f"admin:{model._meta.app_label}_{model.__name__.lower()}_changelist"
        )

        # add the admin user to the mocked request and disable CSRF checks
        request = self.factory.post(change_url, data=data, follow=True)
        request.user = self.admin
        request._dont_enforce_csrf_checks = True

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        # get the _cancel custom Django Admin Action
        action_fn = model_admin.get_actions(request)[data.get("action")][0]

        with patch.object(
            subscription, "_api_delete", side_effect=mock_instance_api_retrieve
        ) as patched__api_delete:
            # invoke the _cancel action
            action_fn(model_admin, request, [subscription])

        patched__api_delete.assert_called_once_with()


class TestAdminRegisteredModels(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@djstripe.com", password="xxx"
        )
        self.factory = RequestFactory()
        # the 2 models that do not inherit from StripeModel and hence
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
