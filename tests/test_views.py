"""
dj-stripe Views Tests.
"""
from copy import deepcopy

import pytest
import stripe
from django.apps import apps
from django.contrib import messages
from django.contrib.admin import helpers, site
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test.client import RequestFactory
from django.urls import reverse
from pytest_django.asserts import assertContains, assertQuerysetEqual

from djstripe import models
from djstripe.views import ConfirmCustomAction
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

from .fields.models import TestCustomActionModel

pytestmark = pytest.mark.django_db


class TestConfirmCustomActionView:
    # the 4 models that do not inherit from StripeModel and hence
    # do not inherit from StripeModelAdmin
    ignore_models = [
        "WebhookEventTrigger",
        "WebhookEndpoint",
        "IdempotencyKey",
        "APIKey",
    ]
    kwargs_called_with = {}

    # to get around Session/MessageMiddleware Deprecation Warnings
    def dummy_get_response(self, request):
        return None

    @pytest.mark.parametrize("fake_selected_pks", [None, [1, 2]])
    def test__sync_all_instances(self, fake_selected_pks):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys() and (
                model.__name__ == "WebhookEndpoint"
                or model.__name__ not in self.ignore_models
            ):

                data = {"action": "_sync_all_instances"}

                if fake_selected_pks is not None:
                    data[helpers.ACTION_CHECKBOX_NAME] = fake_selected_pks

                kwargs = {
                    "action_name": "_sync_all_instances",
                    "model_name": model.__name__.lower(),
                    "model_pks": "all",
                }

                # get the custom action POST url
                change_url = reverse(
                    "djstripe:djstripe_custom_action",
                    kwargs=kwargs,
                )

                request = RequestFactory().post(change_url, data=data, follow=True)

                # Add the session/message middleware to the request
                SessionMiddleware(self.dummy_get_response).process_request(request)
                MessageMiddleware(self.dummy_get_response).process_request(request)

                view = ConfirmCustomAction()
                view.setup(request, **kwargs)

                # Invoke the Custom Actions
                view._sync_all_instances(request, model.objects.none())

                # assert correct Success messages are emmitted
                messages_sent_dictionary = {
                    m.message: m.level_tag for m in messages.get_messages(request)
                }

                # assert correct success message was emmitted
                assert (
                    messages_sent_dictionary.get("Successfully Synced All Instances")
                    == "success"
                )

    @pytest.mark.parametrize("djstripe_owner_account_exists", [False, True])
    def test__resync_instances(self, djstripe_owner_account_exists, monkeypatch):
        model = TestCustomActionModel

        # create instance to be used in the Django Admin Action
        instance = model.objects.create(id="test")

        if djstripe_owner_account_exists:
            account_instance = models.Account.objects.first()
            instance.djstripe_owner_account = account_instance
            instance.save()

        data = {
            "action": "_resync_instances",
            helpers.ACTION_CHECKBOX_NAME: [instance.pk],
        }

        # monkeypatch instance.api_retrieve, instance.__class__.sync_from_stripe_data, and app_config.get_model
        def mock_instance_api_retrieve(*args, **keywargs):
            self.kwargs_called_with = keywargs

        def mock_instance_sync_from_stripe_data(*args, **kwargs):
            pass

        def mock_get_model(*args, **kwargs):
            return model

        monkeypatch.setattr(model, "api_retrieve", mock_instance_api_retrieve)

        monkeypatch.setattr(
            model,
            "sync_from_stripe_data",
            mock_instance_sync_from_stripe_data,
        )

        monkeypatch.setattr(ConfirmCustomAction.app_config, "get_model", mock_get_model)

        kwargs = {
            "action_name": "_resync_instances",
            "model_name": model.__name__.lower(),
            "model_pks": str(instance.pk),
        }

        # get the custom action POST url
        change_url = reverse("djstripe:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the Custom Actions
        view._resync_instances(request, [instance])

        # assert correct Success messages are emmitted
        messages_sent_dictionary = {
            m.message: m.level_tag for m in messages.get_messages(request)
        }

        # assert correct success message was emmitted
        assert (
            messages_sent_dictionary.get(f"Successfully Synced: {instance}")
            == "success"
        )

        if djstripe_owner_account_exists:
            # assert in case djstripe_owner_account exists that kwargs are not empty
            assert self.kwargs_called_with == {
                "stripe_account": instance.djstripe_owner_account.id,
                "api_key": instance.default_api_key,
            }
        else:
            # assert in case djstripe_owner_account does not exist that kwargs are empty
            assert self.kwargs_called_with == {}

    def test__resync_instances_stripe_permission_error(self, monkeypatch):

        model = TestCustomActionModel

        # create instance to be used in the Django Admin Action
        instance = model.objects.create(id="test")

        data = {
            "action": "_resync_instances",
            helpers.ACTION_CHECKBOX_NAME: [instance.pk],
        }

        # monkeypatch instance.api_retrieve and app_config.get_model
        def mock_instance_api_retrieve(*args, **kwargs):
            raise stripe.error.PermissionError("some random error message")

        def mock_get_model(*args, **kwargs):
            return model

        monkeypatch.setattr(instance, "api_retrieve", mock_instance_api_retrieve)
        monkeypatch.setattr(ConfirmCustomAction.app_config, "get_model", mock_get_model)

        kwargs = {
            "action_name": "_resync_instances",
            "model_name": model.__name__.lower(),
            "model_pks": str(instance.pk),
        }

        # get the custom action POST url
        change_url = reverse("djstripe:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the Custom Actions
        view._resync_instances(request, [instance])

        # assert correct Success messages are emmitted
        messages_sent_dictionary = {
            m.message.user_message: m.level_tag for m in messages.get_messages(request)
        }

        # assert correct success message was emmitted
        assert messages_sent_dictionary.get("some random error message") == "warning"

    def test__resync_instances_stripe_invalid_request_error(self, monkeypatch):
        model = TestCustomActionModel

        # create instance to be used in the Django Admin Action
        instance = model.objects.create(id="test")

        data = {
            "action": "_resync_instances",
            helpers.ACTION_CHECKBOX_NAME: [instance.pk],
        }

        # monkeypatch instance.api_retrieve and app_config.get_model
        def mock_instance_api_retrieve(*args, **kwargs):
            raise stripe.error.InvalidRequestError({}, "some random error message")

        def mock_get_model(*args, **kwargs):
            return model

        monkeypatch.setattr(instance, "api_retrieve", mock_instance_api_retrieve)
        monkeypatch.setattr(ConfirmCustomAction.app_config, "get_model", mock_get_model)

        kwargs = {
            "action_name": "_resync_instances",
            "model_name": model.__name__.lower(),
            "model_pks": str(instance.pk),
        }

        # get the custom action POST url
        change_url = reverse("djstripe:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        with pytest.raises(stripe.error.InvalidRequestError) as exc_info:
            # Invoke the Custom Actions
            view._resync_instances(request, [instance])

        assert str(exc_info.value.param) == "some random error message"

    @pytest.mark.parametrize(
        "action_name", ["_resync_instances", "_sync_all_instances", "_cancel"]
    )
    def test_post(self, action_name, monkeypatch):
        model = TestCustomActionModel

        # create instance to be used in the Django Admin Action
        instance = model.objects.create(id="test")

        data = {
            "action": action_name,
            helpers.ACTION_CHECKBOX_NAME: [instance.pk],
        }

        # monkeypatch instance.api_retrieve, instance.cancel, instance.__class__.sync_from_stripe_data, and app_config.get_model
        def mock_instance_api_retrieve(*args, **keywargs):
            pass

        def mock_subscription_cancel(*args, **keywargs):
            pass

        def mock_instance_sync_from_stripe_data(*args, **kwargs):
            pass

        def mock_get_model(*args, **kwargs):
            return model

        monkeypatch.setattr(model, "api_retrieve", mock_instance_api_retrieve)

        monkeypatch.setattr(model, "cancel", mock_subscription_cancel)

        monkeypatch.setattr(
            model,
            "sync_from_stripe_data",
            mock_instance_sync_from_stripe_data,
        )

        monkeypatch.setattr(ConfirmCustomAction.app_config, "get_model", mock_get_model)

        kwargs = {
            "action_name": action_name,
            "model_name": model.__name__.lower(),
            "model_pks": str(instance.pk),
        }

        if action_name == "_sync_all_instances":
            kwargs["model_pks"] = "all"

        # get the custom action POST url
        change_url = reverse("djstripe:djstripe_custom_action", kwargs=kwargs)

        # add the admin user to the mocked request and disable CSRF checks
        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the Post method
        response = view.post(request)

        # assert user redirected to the correct url
        assert response.status_code == 302
        assert response.url == reverse(
            f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
        )

    @pytest.mark.parametrize(
        "action_name", ["_resync_instances", "_sync_all_instances", "_cancel"]
    )
    def test_get_queryset(self, action_name, monkeypatch):
        model = TestCustomActionModel

        # create instance to be used in the Django Admin Action
        instance = model.objects.create(id="test")

        data = {
            "action": action_name,
            helpers.ACTION_CHECKBOX_NAME: [instance.pk],
        }

        # monkeypatch app_config.get_model

        def mock_get_model(*args, **kwargs):
            return model

        monkeypatch.setattr(ConfirmCustomAction.app_config, "get_model", mock_get_model)

        kwargs = {
            "action_name": action_name,
            "model_name": model.__name__.lower(),
            "model_pks": str(instance.pk),
        }

        if action_name == "_sync_all_instances":
            kwargs["model_pks"] = "all"

        # get the custom action POST url
        change_url = reverse("djstripe:djstripe_custom_action", kwargs=kwargs)

        # add the admin user to the mocked request and disable CSRF checks
        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the get_queryset method
        qs = view.get_queryset()

        # assert correct queryset gets returned
        if action_name == "_sync_all_instances":
            assertQuerysetEqual(qs, model.objects.all())
            assert qs[0] == instance
        else:
            assertQuerysetEqual(qs, model.objects.filter(pk__in=[instance.pk]))
            assert qs[0] == instance

    @pytest.mark.parametrize(
        "action_name", ["_resync_instances", "_sync_all_instances", "_cancel"]
    )
    def test_get_context_data(self, action_name, monkeypatch):
        model = TestCustomActionModel

        # create instance to be used in the Django Admin Action
        instance = model.objects.create(id="test")

        # monkeypatch app_config.get_model
        def mock_get_model(*args, **kwargs):
            return model

        monkeypatch.setattr(ConfirmCustomAction.app_config, "get_model", mock_get_model)

        kwargs = {
            "action_name": action_name,
            "model_name": model.__name__.lower(),
            "model_pks": str(instance.pk),
        }

        if action_name == "_sync_all_instances":
            kwargs["model_pks"] = "all"

        # get the custom action POST url
        change_url = reverse("djstripe:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().get(change_url)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the get_queryset method
        context = view.get_context_data()

        assert (
            context["info"][0]
            == f'Test custom action model: <a href="/admin/fields/testcustomactionmodel/{instance.pk}/change/">&lt;id=test&gt;</a>'
        )

    @pytest.mark.parametrize(
        "action_name", ["_resync_instances", "_sync_all_instances", "_cancel"]
    )
    def test_get(self, action_name, monkeypatch):
        model = TestCustomActionModel

        # create instance to be used in the Django Admin Action
        instance = model.objects.create(id="test")

        # monkeypatch app_config.get_model
        def mock_get_model(*args, **kwargs):
            return model

        monkeypatch.setattr(ConfirmCustomAction.app_config, "get_model", mock_get_model)

        kwargs = {
            "action_name": action_name,
            "model_name": model.__name__.lower(),
            "model_pks": str(instance.pk),
        }

        if action_name == "_sync_all_instances":
            kwargs["model_pks"] = "all"

        # get the custom action POST url
        change_url = reverse("djstripe:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().get(change_url)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the get method
        response = view.get(request)

        assert response.status_code == 200

        assertContains(response, "Test custom action model: ")

    @pytest.mark.parametrize(
        "action_name", ["_resync_instances", "_sync_all_instances", "_cancel"]
    )
    @pytest.mark.parametrize("is_admin_user", [True, False])
    def test_dispatch(self, is_admin_user, action_name, admin_user, monkeypatch):

        model = TestCustomActionModel

        # create instance to be used in the Django Admin Action
        instance = model.objects.create(id="test")

        # monkeypatch app_config.get_model
        def mock_get_model(*args, **kwargs):
            return model

        monkeypatch.setattr(ConfirmCustomAction.app_config, "get_model", mock_get_model)

        kwargs = {
            "action_name": action_name,
            "model_name": model.__name__.lower(),
            "model_pks": str(instance.pk),
        }

        # get the custom action POST url
        change_url = reverse("djstripe:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().get(change_url)

        if is_admin_user:
            # add the admin user to the mocked request
            request.user = admin_user
        else:
            # add the AnonymousUser to the mocked request
            request.user = AnonymousUser()

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the dispatch method
        response = view.dispatch(request)

        if is_admin_user:
            assert response.status_code == 200
        else:
            assert response.status_code == 302
            assert (
                response.url
                == f"/admin/login/?next=/djstripe/action/{action_name}/testcustomactionmodel/{instance.pk}"
            )

    def test__cancel_subscription_instances(  # noqa: C901
        self,
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

        model = models.Subscription
        # Create Latest Invoice
        models.Invoice.sync_from_stripe_data(FAKE_INVOICE)

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        instance = model.sync_from_stripe_data(subscription_fake)

        def mock_subscription_cancel(*args, **keywargs):
            return instance

        monkeypatch.setattr(instance, "cancel", mock_subscription_cancel)

        data = {"action": "_cancel", helpers.ACTION_CHECKBOX_NAME: [instance.pk]}

        kwargs = {
            "action_name": "_cancel",
            "model_name": model.__name__.lower(),
            "model_pks": str(instance.pk),
        }

        # get the custom action POST url
        change_url = reverse("djstripe:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the Custom Actions
        view._cancel(request, [instance])

        # assert correct Success messages are emmitted
        messages_sent_dictionary = {
            m.message: m.level_tag for m in messages.get_messages(request)
        }

        # assert correct success message was emmitted
        assert (
            messages_sent_dictionary.get(f"Successfully Canceled: {instance}")
            == "success"
        )

    def test__cancel_subscription_instances_stripe_invalid_request_error(  # noqa: C901
        self,
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

        model = models.Subscription
        # Create Latest Invoice
        models.Invoice.sync_from_stripe_data(FAKE_INVOICE)

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        instance = model.sync_from_stripe_data(subscription_fake)

        def mock_subscription_cancel(*args, **keywargs):
            raise stripe.error.InvalidRequestError({}, "some random error message")

        monkeypatch.setattr(instance, "cancel", mock_subscription_cancel)

        data = {"action": "_cancel", helpers.ACTION_CHECKBOX_NAME: [instance.pk]}

        kwargs = {
            "action_name": "_cancel",
            "model_name": model.__name__.lower(),
            "model_pks": str(instance.pk),
        }

        # get the custom action POST url
        change_url = reverse("djstripe:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        with pytest.warns(None, match=r"some random error message"):
            # Invoke the Custom Actions
            view._cancel(request, [instance])
