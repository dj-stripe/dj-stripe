"""
dj-stripe Views Tests.
"""
from copy import deepcopy

import pytest
import stripe
from django.apps import apps
from django.contrib import messages
from django.contrib.admin import helpers, site
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test.client import RequestFactory
from django.urls import reverse
from pytest_django.asserts import assertContains

from djstripe import models, utils
from djstripe.admin.views import ConfirmCustomAction
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

    @pytest.mark.parametrize(
        "action_name",
        [
            "_resync_instances",
            "_sync_all_instances",
            "_cancel",
            "_release_subscription_schedule",
            "_cancel_subscription_schedule",
        ],
    )
    def test_get_form_kwargs(self, action_name, admin_user, monkeypatch):

        model = CustomActionModel

        # monkeypatch utils.get_model
        def mock_get_model(*args, **kwargs):
            return model

        monkeypatch.setattr(utils, "get_model", mock_get_model)

        kwargs = {
            "action_name": action_name,
            "model_name": model.__name__.lower(),
        }

        # get the custom action POST url
        change_url = reverse("admin:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().get(change_url)
        # add the admin user to the mocked request
        request.user = admin_user

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the get_form_kwargs method
        form_kwargs = view.get_form_kwargs()
        assert form_kwargs.get("model_name") == model.__name__.lower()
        assert form_kwargs.get("action_name") == action_name

    @pytest.mark.parametrize(
        "action_name",
        [
            "_resync_instances",
            "_sync_all_instances",
            "_cancel",
            "_release_subscription_schedule",
            "_cancel_subscription_schedule",
        ],
    )
    @pytest.mark.parametrize("djstripe_owner_account_exists", [False, True])
    def test_form_valid(self, djstripe_owner_account_exists, action_name, monkeypatch):
        model = CustomActionModel

        # create instance to be used in the Django Admin Action
        instance = model.objects.create(id="test")

        if djstripe_owner_account_exists:
            account_instance = models.Account.objects.first()
            instance.djstripe_owner_account = account_instance
            instance.save()

        data = {
            "action": action_name,
            helpers.ACTION_CHECKBOX_NAME: [instance.pk],
        }

        if action_name == "_sync_all_instances":
            data[helpers.ACTION_CHECKBOX_NAME] = ["_sync_all_instances"]

        # monkeypatch utils.get_model and
        def mock_get_model(*args, **kwargs):
            return model

        monkeypatch.setattr(utils, "get_model", mock_get_model)

        kwargs = {
            "action_name": action_name,
            "model_name": model.__name__.lower(),
        }

        # get the custom action POST url
        change_url = reverse("admin:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # monkeypatch Request Handler
        def mock_request_handler(*args, **kwargs):
            return None

        monkeypatch.setattr(view, action_name, mock_request_handler)

        # get the form
        form = view.get_form()

        # Ensure form is valid
        assert form.is_valid()

        # Invoke form_valid()
        response = view.form_valid(form)

        # assert user redirected to the correct url
        assert response.status_code == 302
        assert response.url == "/admin/fields/customactionmodel/"

    @pytest.mark.parametrize(
        "action_name",
        [
            "_resync_instances",
            "_sync_all_instances",
            "_cancel",
            "_release_subscription_schedule",
            "_cancel_subscription_schedule",
        ],
    )
    @pytest.mark.parametrize("djstripe_owner_account_exists", [False, True])
    def test_form_invalid(
        self, djstripe_owner_account_exists, action_name, monkeypatch
    ):
        model = CustomActionModel

        # create instance to be used in the Django Admin Action
        instance = model.objects.create(id="test")

        if djstripe_owner_account_exists:
            account_instance = models.Account.objects.first()
            instance.djstripe_owner_account = account_instance
            instance.save()

        data = {
            "action": action_name,
        }

        # monkeypatch utils.get_model and
        def mock_get_model(*args, **kwargs):
            return model

        monkeypatch.setattr(utils, "get_model", mock_get_model)

        kwargs = {
            "action_name": action_name,
            "model_name": model.__name__.lower(),
        }

        # get the custom action POST url
        change_url = reverse("admin:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # get the form
        form = view.get_form()

        # Ensure form is not valid
        assert not form.is_valid()

        # Invoke form_invalid()
        response = view.form_invalid(form)

        # assert user got redirected to the action page with the error rendered
        assertContains(
            response,
            '<ul class="messagelist">\n              <li class="error">* This field is required.</li>\n            </ul>',
            html=True,
        )

    @pytest.mark.parametrize("fake_selected_pks", [None, [1, 2]])
    def test__sync_all_instances(self, fake_selected_pks, monkeypatch):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        all_models_lst = app_config.get_models()

        for model in all_models_lst:
            if model in site._registry.keys() and (
                model.__name__ == "WebhookEndpoint"
                or model.__name__ not in self.ignore_models
            ):

                # monkeypatch utils.get_model
                def mock_get_model(*args, **kwargs):
                    return model

                monkeypatch.setattr(utils, "get_model", mock_get_model)

                data = {"action": "_sync_all_instances"}

                if fake_selected_pks is not None:
                    data[helpers.ACTION_CHECKBOX_NAME] = fake_selected_pks

                kwargs = {
                    "action_name": "_sync_all_instances",
                    "model_name": model.__name__.lower(),
                }

                # get the custom action POST url
                change_url = reverse(
                    "admin:djstripe_custom_action",
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

                # assert correct Success messages are emitted
                messages_sent_dictionary = {
                    m.message: m.level_tag for m in messages.get_messages(request)
                }

                # assert correct success message was emitted
                assert (
                    messages_sent_dictionary.get("Successfully Synced All Instances")
                    == "success"
                )

    @pytest.mark.parametrize("djstripe_owner_account_exists", [False, True])
    def test__resync_instances(self, djstripe_owner_account_exists, monkeypatch):
        model = CustomActionModel

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

        monkeypatch.setattr(utils, "get_model", mock_get_model)

        kwargs = {
            "action_name": "_resync_instances",
            "model_name": model.__name__.lower(),
        }

        # get the custom action POST url
        change_url = reverse("admin:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the Custom Actions
        view._resync_instances(request, [instance])

        # assert correct Success messages are emitted
        messages_sent_dictionary = {
            m.message: m.level_tag for m in messages.get_messages(request)
        }

        # assert correct success message was emitted
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

        model = CustomActionModel

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
        monkeypatch.setattr(utils, "get_model", mock_get_model)

        kwargs = {
            "action_name": "_resync_instances",
            "model_name": model.__name__.lower(),
        }

        # get the custom action POST url
        change_url = reverse("admin:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the Custom Actions
        view._resync_instances(request, [instance])

        # assert correct Success messages are emitted
        messages_sent_dictionary = {
            m.message.user_message: m.level_tag for m in messages.get_messages(request)
        }

        # assert correct success message was emitted
        assert messages_sent_dictionary.get("some random error message") == "warning"

    def test__resync_instances_stripe_invalid_request_error(self, monkeypatch):
        model = CustomActionModel

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
        monkeypatch.setattr(utils, "get_model", mock_get_model)

        kwargs = {
            "action_name": "_resync_instances",
            "model_name": model.__name__.lower(),
        }

        # get the custom action POST url
        change_url = reverse("admin:djstripe_custom_action", kwargs=kwargs)

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

    def test__cancel_subscription_instances(
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

        # monkeypatch subscription.cancel()
        def mock_subscription_cancel(*args, **keywargs):
            return instance

        monkeypatch.setattr(instance, "cancel", mock_subscription_cancel)

        data = {"action": "_cancel", helpers.ACTION_CHECKBOX_NAME: [instance.pk]}

        kwargs = {
            "action_name": "_cancel",
            "model_name": model.__name__.lower(),
        }

        # get the custom action POST url
        change_url = reverse("admin:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the Custom Actions
        view._cancel(request, [instance])

        # assert correct Success messages are emitted
        messages_sent_dictionary = {
            m.message: m.level_tag for m in messages.get_messages(request)
        }

        # assert correct success message was emitted
        assert (
            messages_sent_dictionary.get(f"Successfully Canceled: {instance}")
            == "success"
        )

    def test__cancel_subscription_instances_stripe_invalid_request_error(
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

        # monkeypatch subscription.cancel()
        def mock_subscription_cancel(*args, **keywargs):
            raise stripe.error.InvalidRequestError({}, "some random error message")

        monkeypatch.setattr(instance, "cancel", mock_subscription_cancel)

        data = {"action": "_cancel", helpers.ACTION_CHECKBOX_NAME: [instance.pk]}

        kwargs = {
            "action_name": "_cancel",
            "model_name": model.__name__.lower(),
        }

        # get the custom action POST url
        change_url = reverse("admin:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        with pytest.warns(None, match=r"some random error message"):
            # Invoke the Custom Actions
            view._cancel(request, [instance])

    def test__release_subscription_schedule(
        self,
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

        # monkeypatch subscription_schedule.release()
        def mock_subscription_schedule_release(*args, **keywargs):
            return instance

        monkeypatch.setattr(instance, "release", mock_subscription_schedule_release)

        data = {
            "action": "_release_subscription_schedule",
            helpers.ACTION_CHECKBOX_NAME: [instance.pk],
        }

        kwargs = {
            "action_name": "_release_subscription_schedule",
            "model_name": model.__name__.lower(),
        }

        # get the custom action POST url
        change_url = reverse("admin:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the Custom Actions
        view._release_subscription_schedule(request, [instance])

        # assert correct Success messages are emitted
        messages_sent_dictionary = {
            m.message: m.level_tag for m in messages.get_messages(request)
        }

        # assert correct success message was emitted
        assert (
            messages_sent_dictionary.get(f"Successfully Released: {instance}")
            == "success"
        )

    def test__cancel_subscription_schedule(
        self,
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

        # monkeypatch subscription_schedule.cancel()
        def mock_subscription_schedule_cancel(*args, **keywargs):
            return instance

        monkeypatch.setattr(instance, "cancel", mock_subscription_schedule_cancel)

        data = {
            "action": "_cancel_subscription_schedule",
            helpers.ACTION_CHECKBOX_NAME: [instance.pk],
        }

        kwargs = {
            "action_name": "_cancel_subscription_schedule",
            "model_name": model.__name__.lower(),
        }

        # get the custom action POST url
        change_url = reverse("admin:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        # Invoke the Custom Actions
        view._cancel_subscription_schedule(request, [instance])

        # assert correct Success messages are emitted
        messages_sent_dictionary = {
            m.message: m.level_tag for m in messages.get_messages(request)
        }

        # assert correct success message was emitted
        assert (
            messages_sent_dictionary.get(f"Successfully Canceled: {instance}")
            == "success"
        )

    def test__release_subscription_schedule_stripe_invalid_request_error(
        self,
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

        # monkeypatch subscription_schedule.release()
        def mock_subscription_schedule_release(*args, **keywargs):
            raise stripe.error.InvalidRequestError({}, "some random error message")

        monkeypatch.setattr(instance, "release", mock_subscription_schedule_release)

        data = {
            "action": "_release_subscription_schedule",
            helpers.ACTION_CHECKBOX_NAME: [instance.pk],
        }

        kwargs = {
            "action_name": "_release_subscription_schedule",
            "model_name": model.__name__.lower(),
        }

        # get the custom action POST url
        change_url = reverse("admin:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        with pytest.warns(None, match=r"some random error message"):
            # Invoke the Custom Actions
            view._release_subscription_schedule(request, [instance])

    def test__cancel_subscription_schedule_stripe_invalid_request_error(
        self,
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

        # monkeypatch subscription_schedule.cancel()
        def mock_subscription_schedule_cancel(*args, **keywargs):
            raise stripe.error.InvalidRequestError({}, "some random error message")

        monkeypatch.setattr(instance, "cancel", mock_subscription_schedule_cancel)

        data = {
            "action": "_cancel_subscription_schedule",
            helpers.ACTION_CHECKBOX_NAME: [instance.pk],
        }

        kwargs = {
            "action_name": "_cancel_subscription_schedule",
            "model_name": model.__name__.lower(),
        }

        # get the custom action POST url
        change_url = reverse("admin:djstripe_custom_action", kwargs=kwargs)

        request = RequestFactory().post(change_url, data=data, follow=True)

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        view = ConfirmCustomAction()
        view.setup(request, **kwargs)

        with pytest.warns(None, match=r"some random error message"):
            # Invoke the Custom Actions
            view._cancel_subscription_schedule(request, [instance])
