"""
dj-stripe Event Handler tests
"""
from copy import deepcopy
from decimal import Decimal
from unittest.mock import ANY, call, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from stripe.error import InvalidRequestError

from djstripe.enums import SubscriptionStatus
from djstripe.models import (
    Card,
    Charge,
    Coupon,
    Customer,
    Dispute,
    DjstripePaymentMethod,
    Event,
    Invoice,
    InvoiceItem,
    PaymentMethod,
    Plan,
    Price,
    Subscription,
    SubscriptionSchedule,
    Transfer,
)
from djstripe.models.account import Account
from djstripe.models.billing import TaxId
from djstripe.models.checkout import Session
from djstripe.models.core import File
from djstripe.models.orders import Order
from djstripe.models.payment_methods import BankAccount

from . import (
    FAKE_ACCOUNT,
    FAKE_BALANCE_TRANSACTION,
    FAKE_BANK_ACCOUNT_IV,
    FAKE_CARD,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CARD_II,
    FAKE_CARD_III,
    FAKE_CARD_IV,
    FAKE_CHARGE,
    FAKE_CHARGE_II,
    FAKE_COUPON,
    FAKE_CUSTOM_ACCOUNT,
    FAKE_CUSTOMER,
    FAKE_CUSTOMER_II,
    FAKE_DISPUTE_BALANCE_TRANSACTION,
    FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_FULL,
    FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_PARTIAL,
    FAKE_DISPUTE_CHARGE,
    FAKE_DISPUTE_I,
    FAKE_DISPUTE_II,
    FAKE_DISPUTE_III,
    FAKE_DISPUTE_PAYMENT_INTENT,
    FAKE_DISPUTE_PAYMENT_METHOD,
    FAKE_DISPUTE_V_FULL,
    FAKE_DISPUTE_V_PARTIAL,
    FAKE_EVENT_ACCOUNT_APPLICATION_AUTHORIZED,
    FAKE_EVENT_ACCOUNT_APPLICATION_DEAUTHORIZED,
    FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_CREATED,
    FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_DELETED,
    FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_UPDATED,
    FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_CREATED,
    FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_DELETED,
    FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_UPDATED,
    FAKE_EVENT_CARD_PAYMENT_METHOD_ATTACHED,
    FAKE_EVENT_CARD_PAYMENT_METHOD_DETACHED,
    FAKE_EVENT_CHARGE_SUCCEEDED,
    FAKE_EVENT_CUSTOM_ACCOUNT_UPDATED,
    FAKE_EVENT_CUSTOMER_CREATED,
    FAKE_EVENT_CUSTOMER_DELETED,
    FAKE_EVENT_CUSTOMER_DISCOUNT_CREATED,
    FAKE_EVENT_CUSTOMER_DISCOUNT_DELETED,
    FAKE_EVENT_CUSTOMER_SOURCE_CREATED,
    FAKE_EVENT_CUSTOMER_SOURCE_DELETED,
    FAKE_EVENT_CUSTOMER_SOURCE_DELETED_DUPE,
    FAKE_EVENT_CUSTOMER_SUBSCRIPTION_CREATED,
    FAKE_EVENT_CUSTOMER_SUBSCRIPTION_DELETED,
    FAKE_EVENT_CUSTOMER_UPDATED,
    FAKE_EVENT_DISPUTE_CLOSED,
    FAKE_EVENT_DISPUTE_CREATED,
    FAKE_EVENT_DISPUTE_FUNDS_REINSTATED_FULL,
    FAKE_EVENT_DISPUTE_FUNDS_REINSTATED_PARTIAL,
    FAKE_EVENT_DISPUTE_FUNDS_WITHDRAWN,
    FAKE_EVENT_DISPUTE_UPDATED,
    FAKE_EVENT_EXPRESS_ACCOUNT_UPDATED,
    FAKE_EVENT_FILE_CREATED,
    FAKE_EVENT_INVOICE_CREATED,
    FAKE_EVENT_INVOICE_DELETED,
    FAKE_EVENT_INVOICE_UPCOMING,
    FAKE_EVENT_INVOICEITEM_CREATED,
    FAKE_EVENT_INVOICEITEM_DELETED,
    FAKE_EVENT_ORDER_CANCELLED,
    FAKE_EVENT_ORDER_COMPLETED,
    FAKE_EVENT_ORDER_CREATED,
    FAKE_EVENT_ORDER_PROCESSING,
    FAKE_EVENT_ORDER_SUBMITTED,
    FAKE_EVENT_ORDER_UPDATED,
    FAKE_EVENT_PAYMENT_INTENT_SUCCEEDED_DESTINATION_CHARGE,
    FAKE_EVENT_PAYMENT_METHOD_ATTACHED,
    FAKE_EVENT_PAYMENT_METHOD_DETACHED,
    FAKE_EVENT_PLAN_CREATED,
    FAKE_EVENT_PLAN_DELETED,
    FAKE_EVENT_PLAN_REQUEST_IS_OBJECT,
    FAKE_EVENT_PRICE_CREATED,
    FAKE_EVENT_PRICE_DELETED,
    FAKE_EVENT_PRICE_UPDATED,
    FAKE_EVENT_SESSION_COMPLETED,
    FAKE_EVENT_STANDARD_ACCOUNT_UPDATED,
    FAKE_EVENT_SUBSCRIPTION_SCHEDULE_ABORTED,
    FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CANCELED,
    FAKE_EVENT_SUBSCRIPTION_SCHEDULE_COMPLETED,
    FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED,
    FAKE_EVENT_SUBSCRIPTION_SCHEDULE_EXPIRING,
    FAKE_EVENT_SUBSCRIPTION_SCHEDULE_RELEASED,
    FAKE_EVENT_SUBSCRIPTION_SCHEDULE_UPDATED,
    FAKE_EVENT_TAX_ID_CREATED,
    FAKE_EVENT_TAX_ID_DELETED,
    FAKE_EVENT_TAX_ID_UPDATED,
    FAKE_EVENT_TRANSFER_CREATED,
    FAKE_EVENT_TRANSFER_DELETED,
    FAKE_EXPRESS_ACCOUNT,
    FAKE_FILEUPLOAD_ICON,
    FAKE_FILEUPLOAD_LOGO,
    FAKE_INVOICE,
    FAKE_INVOICE_II,
    FAKE_INVOICEITEM,
    FAKE_PAYMENT_INTENT_DESTINATION_CHARGE,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PAYMENT_INTENT_II,
    FAKE_PAYMENT_METHOD_I,
    FAKE_PAYMENT_METHOD_II,
    FAKE_PLAN,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_PRICE,
    FAKE_PRODUCT,
    FAKE_SESSION_I,
    FAKE_STANDARD_ACCOUNT,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_CANCELED,
    FAKE_SUBSCRIPTION_III,
    FAKE_SUBSCRIPTION_SCHEDULE,
    FAKE_TAX_ID,
    FAKE_TAX_ID_UPDATED,
    FAKE_TRANSFER,
    AssertStripeFksMixin,
)


class EventTestCase(TestCase):
    #
    # Helpers
    #

    @patch("stripe.Event.retrieve", autospec=True)
    def _create_event(self, event_data, event_retrieve_mock, patch_data=None):
        event_data = deepcopy(event_data)

        if patch_data:
            event_data.update(patch_data)

        event_retrieve_mock.return_value = event_data
        event = Event.sync_from_stripe_data(event_data)

        return event


class TestAccountEvents(EventTestCase):
    def setUp(self):
        # create a Custom Stripe Account
        self.custom_account = FAKE_CUSTOM_ACCOUNT.create()

        # create a Standard Stripe Account
        self.standard_account = FAKE_STANDARD_ACCOUNT.create()

        # create an Express Stripe Account
        self.express_account = FAKE_EXPRESS_ACCOUNT.create()

    @patch("stripe.Event.retrieve", autospec=True)
    def test_account_deauthorized_event(self, event_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_ACCOUNT_APPLICATION_DEAUTHORIZED)

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

    @patch("stripe.Event.retrieve", autospec=True)
    def test_account_authorized_event(self, event_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_ACCOUNT_APPLICATION_AUTHORIZED)

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

    # account.external_account.* events are fired for Custom and Express Accounts
    @patch(
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_BANK_ACCOUNT_IV),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_custom_account_external_account_created_bank_account_event(
        self, event_retrieve_mock, account_retrieve_external_account_mock
    ):
        fake_stripe_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_CREATED
        )

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        # fetch the newly created BankAccount object
        bankaccount = BankAccount.objects.get(account=self.custom_account)

        # assert the ids of the Bank Account and the Accounts were synced correctly.
        self.assertEqual(
            bankaccount.id,
            fake_stripe_event["data"]["object"]["id"],
        )
        self.assertEqual(
            self.custom_account.id,
            fake_stripe_event["data"]["object"]["account"],
        )

    @patch(
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_BANK_ACCOUNT_IV),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_custom_account_external_account_deleted_bank_account_event(
        self, event_retrieve_mock, account_retrieve_external_account_mock
    ):
        fake_stripe_create_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_CREATED
        )

        event = Event.sync_from_stripe_data(fake_stripe_create_event)
        event.invoke_webhook_handlers()

        fake_stripe_delete_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_DELETED
        )
        event = Event.sync_from_stripe_data(fake_stripe_delete_event)
        event.invoke_webhook_handlers()

        # assert the BankAccount object no longer exists
        self.assertFalse(
            BankAccount.objects.filter(
                id=fake_stripe_create_event["data"]["object"]["id"]
            ).exists()
        )

    @patch(
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_BANK_ACCOUNT_IV),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_custom_account_external_account_updated_bank_account_event(
        self, event_retrieve_mock, account_retrieve_external_account_mock
    ):
        fake_stripe_create_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_CREATED
        )

        event = Event.sync_from_stripe_data(fake_stripe_create_event)
        event.invoke_webhook_handlers()

        fake_stripe_update_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_UPDATED
        )
        event = Event.sync_from_stripe_data(fake_stripe_update_event)
        event.invoke_webhook_handlers()

        # fetch the updated BankAccount object
        bankaccount = BankAccount.objects.get(account=self.custom_account)

        # assert we are updating the account_holder_name
        self.assertNotEqual(
            fake_stripe_update_event["data"]["object"]["account_holder_name"],
            fake_stripe_create_event["data"]["object"]["account_holder_name"],
        )

        # assert the account_holder_name got updated
        self.assertNotEqual(
            bankaccount.account_holder_name,
            fake_stripe_update_event["data"]["object"]["account_holder_name"],
        )

        # assert the expected BankAccount object got updated
        self.assertEqual(
            bankaccount.id, fake_stripe_create_event["data"]["object"]["id"]
        )

    @patch(
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_CARD_IV),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_custom_account_external_account_created_card_event(
        self, event_retrieve_mock, account_retrieve_external_account_mock
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_CREATED)

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        # fetch the newly created Card object
        card = Card.objects.get(account=self.custom_account)

        # assert the ids of the Card and the Accounts were synced correctly.
        self.assertEqual(
            card.id,
            fake_stripe_event["data"]["object"]["id"],
        )
        self.assertEqual(
            self.custom_account.id,
            fake_stripe_event["data"]["object"]["account"],
        )

    @patch(
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_CARD_IV),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_custom_account_external_account_deleted_card_event(
        self, event_retrieve_mock, account_retrieve_external_account_mock
    ):
        fake_stripe_create_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_CREATED
        )

        event = Event.sync_from_stripe_data(fake_stripe_create_event)
        event.invoke_webhook_handlers()

        fake_stripe_delete_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_DELETED
        )
        event = Event.sync_from_stripe_data(fake_stripe_delete_event)
        event.invoke_webhook_handlers()

        # assert Card Object no longer exists
        self.assertFalse(
            Card.objects.filter(
                id=fake_stripe_create_event["data"]["object"]["id"]
            ).exists()
        )

    @patch(
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_CARD_IV),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_custom_account_external_account_updated_card_event(
        self, event_retrieve_mock, account_retrieve_external_account_mock
    ):
        fake_stripe_create_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_CREATED
        )

        event = Event.sync_from_stripe_data(fake_stripe_create_event)
        event.invoke_webhook_handlers()

        fake_stripe_update_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_UPDATED
        )
        event = Event.sync_from_stripe_data(fake_stripe_update_event)
        event.invoke_webhook_handlers()

        # fetch the updated Card object
        card = Card.objects.get(account=self.custom_account)

        # assert we are updating the name
        self.assertNotEqual(
            fake_stripe_update_event["data"]["object"]["name"],
            fake_stripe_create_event["data"]["object"]["name"],
        )

        # assert the name got updated
        self.assertNotEqual(
            card.name, fake_stripe_update_event["data"]["object"]["name"]
        )

        # assert the expected Card object got updated
        self.assertEqual(card.id, fake_stripe_create_event["data"]["object"]["id"])

    @patch(
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_BANK_ACCOUNT_IV),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_express_account_external_account_created_bank_account_event(
        self, event_retrieve_mock, account_retrieve_external_account_mock
    ):
        fake_stripe_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_CREATED
        )

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        # fetch the newly created BankAccount object
        bankaccount = BankAccount.objects.get(account=self.express_account)

        # assert the ids of the Bank Account and the Accounts were synced correctly.
        self.assertEqual(
            bankaccount.id,
            fake_stripe_event["data"]["object"]["id"],
        )
        self.assertEqual(
            self.express_account.id,
            fake_stripe_event["data"]["object"]["account"],
        )

    @patch(
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_BANK_ACCOUNT_IV),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_express_account_external_account_deleted_bank_account_event(
        self, event_retrieve_mock, account_retrieve_external_account_mock
    ):
        fake_stripe_create_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_CREATED
        )

        event = Event.sync_from_stripe_data(fake_stripe_create_event)
        event.invoke_webhook_handlers()

        fake_stripe_delete_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_DELETED
        )
        event = Event.sync_from_stripe_data(fake_stripe_delete_event)
        event.invoke_webhook_handlers()

        # assert the BankAccount object no longer exists
        self.assertFalse(
            BankAccount.objects.filter(
                id=fake_stripe_create_event["data"]["object"]["id"]
            ).exists()
        )

    @patch(
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_BANK_ACCOUNT_IV),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_express_account_external_account_updated_bank_account_event(
        self, event_retrieve_mock, account_retrieve_external_account_mock
    ):
        fake_stripe_create_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_CREATED
        )

        event = Event.sync_from_stripe_data(fake_stripe_create_event)
        event.invoke_webhook_handlers()

        fake_stripe_update_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_UPDATED
        )
        event = Event.sync_from_stripe_data(fake_stripe_update_event)
        event.invoke_webhook_handlers()

        # fetch the updated BankAccount object
        bankaccount = BankAccount.objects.get(account=self.express_account)

        # assert we are updating the account_holder_name
        self.assertNotEqual(
            fake_stripe_update_event["data"]["object"]["account_holder_name"],
            fake_stripe_create_event["data"]["object"]["account_holder_name"],
        )

        # assert the account_holder_name got updated
        self.assertNotEqual(
            bankaccount.account_holder_name,
            fake_stripe_update_event["data"]["object"]["account_holder_name"],
        )

        # assert the expected BankAccount object got updated
        self.assertEqual(
            bankaccount.id, fake_stripe_create_event["data"]["object"]["id"]
        )

    @patch(
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_CARD_IV),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_express_account_external_account_created_card_event(
        self, event_retrieve_mock, account_retrieve_external_account_mock
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_CREATED)

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        # fetch the newly created Card object
        card = Card.objects.get(account=self.express_account)

        # assert the ids of the Card and the Accounts were synced correctly.
        self.assertEqual(
            card.id,
            fake_stripe_event["data"]["object"]["id"],
        )
        self.assertEqual(
            self.express_account.id,
            fake_stripe_event["data"]["object"]["account"],
        )

    @patch(
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_CARD_IV),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_express_account_external_account_deleted_card_event(
        self, event_retrieve_mock, account_retrieve_external_account_mock
    ):
        fake_stripe_create_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_CREATED
        )

        event = Event.sync_from_stripe_data(fake_stripe_create_event)
        event.invoke_webhook_handlers()

        fake_stripe_delete_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_DELETED
        )
        event = Event.sync_from_stripe_data(fake_stripe_delete_event)
        event.invoke_webhook_handlers()

        # assert Card Object no longer exists
        self.assertFalse(
            Card.objects.filter(
                id=fake_stripe_create_event["data"]["object"]["id"]
            ).exists()
        )

    @patch(
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_CARD_IV),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_express_account_external_account_updated_card_event(
        self, event_retrieve_mock, account_retrieve_external_account_mock
    ):
        fake_stripe_create_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_CREATED
        )

        event = Event.sync_from_stripe_data(fake_stripe_create_event)
        event.invoke_webhook_handlers()

        fake_stripe_update_event = deepcopy(
            FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_UPDATED
        )
        event = Event.sync_from_stripe_data(fake_stripe_update_event)
        event.invoke_webhook_handlers()

        # fetch the updated Card object
        card = Card.objects.get(account=self.express_account)

        # assert we are updating the name
        self.assertNotEqual(
            fake_stripe_update_event["data"]["object"]["name"],
            fake_stripe_create_event["data"]["object"]["name"],
        )

        # assert the name got updated
        self.assertNotEqual(
            card.name, fake_stripe_update_event["data"]["object"]["name"]
        )

        # assert the expected Card object got updated
        self.assertEqual(card.id, fake_stripe_create_event["data"]["object"]["id"])

    # account.updated events

    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_EVENT_STANDARD_ACCOUNT_UPDATED["data"]["object"]),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_standard_account_updated_event(
        self, event_retrieve_mock, account_retrieve_mock
    ):

        # fetch the Stripe Account
        standard_account = self.standard_account

        # assert metadata is empty
        self.assertEqual(standard_account.metadata, {})

        fake_stripe_update_event = deepcopy(FAKE_EVENT_STANDARD_ACCOUNT_UPDATED)

        event = Event.sync_from_stripe_data(fake_stripe_update_event)
        event.invoke_webhook_handlers()

        # fetch the updated Account object
        updated_standard_account = Account.objects.get(id=standard_account.id)

        # assert we are updating the metadata
        self.assertNotEqual(
            updated_standard_account.metadata,
            standard_account.metadata,
        )

        # assert the meta got updated
        self.assertEqual(
            updated_standard_account.metadata,
            fake_stripe_update_event["data"]["object"]["metadata"],
        )

    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_EVENT_EXPRESS_ACCOUNT_UPDATED["data"]["object"]),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_express_account_updated_event(
        self, event_retrieve_mock, account_retrieve_mock
    ):

        # fetch the Stripe Account
        express_account = self.express_account

        # assert metadata is empty
        self.assertEqual(express_account.metadata, {})

        fake_stripe_update_event = deepcopy(FAKE_EVENT_EXPRESS_ACCOUNT_UPDATED)

        event = Event.sync_from_stripe_data(fake_stripe_update_event)
        event.invoke_webhook_handlers()

        # fetch the updated Account object
        updated_express_account = Account.objects.get(id=express_account.id)

        # assert we are updating the metadata
        self.assertNotEqual(
            updated_express_account.metadata,
            express_account.metadata,
        )

        # assert the meta got updated
        self.assertEqual(
            updated_express_account.metadata,
            fake_stripe_update_event["data"]["object"]["metadata"],
        )

    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_EVENT_CUSTOM_ACCOUNT_UPDATED["data"]["object"]),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_custom_account_updated_event(
        self, event_retrieve_mock, account_retrieve_mock
    ):

        # fetch the Stripe Account
        custom_account = self.custom_account

        # assert metadata is empty
        self.assertEqual(custom_account.metadata, {})

        fake_stripe_update_event = deepcopy(FAKE_EVENT_CUSTOM_ACCOUNT_UPDATED)

        event = Event.sync_from_stripe_data(fake_stripe_update_event)
        event.invoke_webhook_handlers()

        # fetch the updated Account object
        updated_custom_account = Account.objects.get(id=custom_account.id)

        # assert we are updating the metadata
        self.assertNotEqual(
            updated_custom_account.metadata,
            custom_account.metadata,
        )

        # assert the meta got updated
        self.assertEqual(
            updated_custom_account.metadata,
            fake_stripe_update_event["data"]["object"]["metadata"],
        )


class TestChargeEvents(EventTestCase):
    def setUp(self):
        # create a Stripe Platform Account
        self.account = FAKE_PLATFORM_ACCOUNT.create()

        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
    )
    @patch("stripe.Charge.retrieve", autospec=True)
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    def test_charge_created(
        self,
        subscription_retrieve_mock,
        product_retrieve_mock,
        invoice_retrieve_mock,
        event_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
        account_mock,
    ):
        FAKE_CUSTOMER.create_for_user(self.user)
        fake_stripe_event = deepcopy(FAKE_EVENT_CHARGE_SUCCEEDED)
        event_retrieve_mock.return_value = fake_stripe_event
        charge_retrieve_mock.return_value = fake_stripe_event["data"]["object"]
        account_mock.return_value = self.account

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        charge = Charge.objects.get(id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(
            charge.amount,
            fake_stripe_event["data"]["object"]["amount"] / Decimal("100"),
        )
        self.assertEqual(charge.status, fake_stripe_event["data"]["object"]["status"])


class TestCheckoutEvents(EventTestCase):
    def setUp(self):

        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

    @patch(
        "stripe.checkout.Session.retrieve", return_value=FAKE_SESSION_I, autospec=True
    )
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
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_checkout_session_completed(
        self,
        event_retrieve_mock,
        payment_intent_retrieve_mock,
        customer_retrieve_mock,
        invoice_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        session_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_SESSION_COMPLETED)
        event_retrieve_mock.return_value = fake_stripe_event

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        session = Session.objects.get(id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(session.customer.id, self.customer.id)

    @patch(
        "stripe.checkout.Session.retrieve", return_value=FAKE_SESSION_I, autospec=True
    )
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
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_checkout_session_async_payment_succeeded(
        self,
        event_retrieve_mock,
        payment_intent_retrieve_mock,
        customer_retrieve_mock,
        invoice_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        session_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_SESSION_COMPLETED)
        fake_stripe_event["type"] = "checkout.session.async_payment_succeeded"

        event_retrieve_mock.return_value = fake_stripe_event

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        session = Session.objects.get(id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(session.customer.id, self.customer.id)

    @patch(
        "stripe.checkout.Session.retrieve", return_value=FAKE_SESSION_I, autospec=True
    )
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
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_checkout_session_async_payment_failed(
        self,
        event_retrieve_mock,
        payment_intent_retrieve_mock,
        customer_retrieve_mock,
        invoice_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        session_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_SESSION_COMPLETED)
        fake_stripe_event["type"] = "checkout.session.async_payment_failed"

        event_retrieve_mock.return_value = fake_stripe_event

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        session = Session.objects.get(id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(session.customer.id, self.customer.id)

    @patch("stripe.checkout.Session.retrieve", autospec=True)
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
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch(
        "stripe.Customer.modify",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=FAKE_PAYMENT_INTENT_I,
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_checkout_session_completed_customer_subscriber_added(
        self,
        event_retrieve_mock,
        payment_intent_retrieve_mock,
        customer_modify_mock,
        invoice_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        session_retrieve_mock,
    ):
        # because create_for_user method adds subscriber
        self.customer.subcriber = None
        self.customer.save()

        # update metadata in deepcopied FAKE_SEESION_1 Object
        fake_stripe_event = deepcopy(FAKE_EVENT_SESSION_COMPLETED)
        fake_stripe_event["data"]["object"]["metadata"] = {
            "djstripe_subscriber": self.user.id
        }
        event_retrieve_mock.return_value = fake_stripe_event

        # update metadata in FAKE_SEESION_1 Object
        fake_stripe_session = deepcopy(FAKE_SESSION_I)
        fake_stripe_session["metadata"] = {"djstripe_subscriber": self.user.id}
        session_retrieve_mock.return_value = fake_stripe_session

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        # refresh self.customer from db
        self.customer.refresh_from_db()

        session = Session.objects.get(id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(session.customer.id, self.customer.id)
        self.assertEqual(self.customer.subscriber, self.user)
        self.assertEqual(self.customer.metadata, {"djstripe_subscriber": self.user.id})


class TestCustomerEvents(EventTestCase):
    def setUp(self):

        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

    @patch("stripe.Customer.retrieve", return_value=FAKE_CUSTOMER, autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_customer_created(self, event_retrieve_mock, customer_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        customer = Customer.objects.get(id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(
            customer.balance, fake_stripe_event["data"]["object"]["balance"]
        )
        self.assertEqual(
            customer.currency, fake_stripe_event["data"]["object"]["currency"]
        )

    @patch("stripe.Customer.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_customer_metadata_created(
        self, event_retrieve_mock, customer_retrieve_mock
    ):

        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["metadata"] = {"djstripe_subscriber": self.user.id}

        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_CREATED)

        fake_stripe_event["data"]["object"] = fake_customer

        event_retrieve_mock.return_value = fake_stripe_event
        customer_retrieve_mock.return_value = fake_customer

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        customer = Customer.objects.get(id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(
            customer.balance, fake_stripe_event["data"]["object"]["balance"]
        )
        self.assertEqual(
            customer.currency, fake_stripe_event["data"]["object"]["currency"]
        )
        self.assertEqual(customer.subscriber, self.user)
        self.assertEqual(customer.metadata, {"djstripe_subscriber": self.user.id})

    @patch("stripe.Customer.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_customer_metadata_updated(
        self, event_retrieve_mock, customer_retrieve_mock
    ):

        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["metadata"] = {"djstripe_subscriber": self.user.id}

        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_UPDATED)

        fake_stripe_event["data"]["object"] = fake_customer

        event_retrieve_mock.return_value = fake_stripe_event
        customer_retrieve_mock.return_value = fake_customer

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        customer = Customer.objects.get(id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(
            customer.balance, fake_stripe_event["data"]["object"]["balance"]
        )
        self.assertEqual(
            customer.currency, fake_stripe_event["data"]["object"]["currency"]
        )
        self.assertEqual(customer.subscriber, self.user)
        self.assertEqual(customer.metadata, {"djstripe_subscriber": self.user.id})

    @patch(
        "stripe.Customer.delete_source",
        autospec=True,
    )
    @patch("stripe.Customer.delete", autospec=True)
    @patch(
        "stripe.Customer.retrieve_source",
        side_effect=[deepcopy(FAKE_CARD), deepcopy(FAKE_CARD_III)],
        autospec=True,
    )
    @patch("stripe.Customer.retrieve", return_value=FAKE_CUSTOMER, autospec=True)
    def test_customer_deleted(
        self,
        customer_retrieve_mock,
        customer_retrieve_source_mock,
        customer_delete_mock,
        customer_source_delete_mock,
    ):

        FAKE_CUSTOMER.create_for_user(self.user)
        event = self._create_event(FAKE_EVENT_CUSTOMER_CREATED)
        event.invoke_webhook_handlers()

        event = self._create_event(FAKE_EVENT_CUSTOMER_DELETED)
        event.invoke_webhook_handlers()
        customer = Customer.objects.get(id=FAKE_CUSTOMER["id"])
        self.assertIsNotNone(customer.date_purged)

    @patch("stripe.Coupon.retrieve", return_value=FAKE_COUPON, autospec=True)
    @patch(
        "stripe.Event.retrieve",
        return_value=FAKE_EVENT_CUSTOMER_DISCOUNT_CREATED,
        autospec=True,
    )
    def test_customer_discount_created(self, event_retrieve_mock, coupon_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_DISCOUNT_CREATED)
        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        self.assertIsNotNone(event.customer)
        self.assertEqual(event.customer.id, FAKE_CUSTOMER["id"])
        self.assertIsNotNone(event.customer.coupon)

    @patch("stripe.Coupon.retrieve", return_value=FAKE_COUPON, autospec=True)
    @patch(
        "stripe.Event.retrieve",
        return_value=FAKE_EVENT_CUSTOMER_DISCOUNT_DELETED,
        autospec=True,
    )
    def test_customer_discount_deleted(self, event_retrieve_mock, coupon_retrieve_mock):
        coupon = Coupon.sync_from_stripe_data(FAKE_COUPON)
        self.customer.coupon = coupon

        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_DISCOUNT_DELETED)
        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        self.assertIsNotNone(event.customer)
        self.assertEqual(event.customer.id, FAKE_CUSTOMER["id"])
        self.assertIsNone(event.customer.coupon)

    @patch("stripe.Customer.retrieve", return_value=FAKE_CUSTOMER, autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    @patch(
        "stripe.Customer.retrieve_source",
        return_value=deepcopy(FAKE_CARD),
        autospec=True,
    )
    def test_customer_card_created(
        self, customer_retrieve_source_mock, event_retrieve_mock, customer_retrieve_mock
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_SOURCE_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        card = Card.objects.get(id=fake_stripe_event["data"]["object"]["id"])
        self.assertIn(card, self.customer.legacy_cards.all())
        self.assertEqual(card.brand, fake_stripe_event["data"]["object"]["brand"])
        self.assertEqual(card.last4, fake_stripe_event["data"]["object"]["last4"])

    @patch("stripe.Event.retrieve", autospec=True)
    @patch("stripe.Customer.retrieve", return_value=FAKE_CUSTOMER, autospec=True)
    def test_customer_unknown_source_created(
        self, customer_retrieve_mock, event_retrieve_mock
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_SOURCE_CREATED)
        fake_stripe_event["data"]["object"]["object"] = "unknown"
        fake_stripe_event["data"]["object"][
            "id"
        ] = "card_xxx_test_customer_unk_source_created"
        event_retrieve_mock.return_value = fake_stripe_event

        FAKE_CUSTOMER.create_for_user(self.user)

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        self.assertFalse(
            Card.objects.filter(id=fake_stripe_event["data"]["object"]["id"]).exists()
        )

    @patch("stripe.Customer.retrieve", return_value=FAKE_CUSTOMER, autospec=True)
    def test_customer_default_source_deleted(self, customer_retrieve_mock):
        self.customer.default_source = DjstripePaymentMethod.objects.get(
            id=FAKE_CARD["id"]
        )
        self.customer.save()
        self.assertIsNotNone(self.customer.default_source)
        with pytest.warns(DeprecationWarning):
            self.assertTrue(self.customer.has_valid_source())

        event = self._create_event(FAKE_EVENT_CUSTOMER_SOURCE_DELETED)
        event.invoke_webhook_handlers()

        # fetch the customer. Doubles up as a check that the customer didn't get
        # deleted
        customer = Customer.objects.get(id=FAKE_CUSTOMER["id"])
        self.assertIsNone(customer.default_source)
        with pytest.warns(DeprecationWarning):
            self.assertFalse(customer.has_valid_source())

    @patch("stripe.Customer.retrieve", return_value=FAKE_CUSTOMER, autospec=True)
    def test_customer_source_double_delete(self, customer_retrieve_mock):
        event = self._create_event(FAKE_EVENT_CUSTOMER_SOURCE_DELETED)
        event.invoke_webhook_handlers()

        event = self._create_event(FAKE_EVENT_CUSTOMER_SOURCE_DELETED_DUPE)
        event.invoke_webhook_handlers()

        # fetch the customer. Doubles up as a check that the customer didn't get
        # deleted
        customer = Customer.objects.get(id=FAKE_CUSTOMER["id"])
        self.assertIsNone(customer.default_source)
        with pytest.warns(DeprecationWarning):
            self.assertFalse(customer.has_valid_source())

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch("stripe.Subscription.retrieve", autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch("stripe.Event.retrieve", autospec=True)
    @patch("stripe.Customer.retrieve", return_value=FAKE_CUSTOMER, autospec=True)
    def test_customer_subscription_created(
        self,
        customer_retrieve_mock,
        event_retrieve_mock,
        product_retrieve_mock,
        subscription_retrieve_mock,
        plan_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_SUBSCRIPTION_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION)
        # latest_invoice has to be None for a Subscription that has not been created yet.
        fake_subscription["latest_invoice"] = None
        subscription_retrieve_mock.return_value = fake_subscription

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        subscription = Subscription.objects.get(
            id=fake_stripe_event["data"]["object"]["id"]
        )
        self.assertIn(subscription, self.customer.subscriptions.all())
        self.assertEqual(
            subscription.status, fake_stripe_event["data"]["object"]["status"]
        )
        self.assertEqual(
            subscription.quantity, fake_stripe_event["data"]["object"]["quantity"]
        )

    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_customer_subscription_deleted(
        self,
        customer_retrieve_mock,
        product_retrieve_mock,
        subscription_retrieve_mock,
        plan_retrieve_mock,
        invoice_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_subscription = deepcopy(FAKE_SUBSCRIPTION)
        # A just created Subscription cannot have latest_invoice
        fake_subscription["latest_invoice"] = None
        subscription_retrieve_mock.return_value = fake_subscription

        fake_event = deepcopy(FAKE_EVENT_CUSTOMER_SUBSCRIPTION_CREATED)
        fake_event["data"]["object"] = fake_subscription

        event = self._create_event(fake_event)
        event.invoke_webhook_handlers()

        sub = Subscription.objects.get(id=fake_subscription["id"])
        self.assertEqual(sub.status, SubscriptionStatus.active)

        # create invoice for latest_invoice in subscription to work.
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        subscription_retrieve_mock.return_value = deepcopy(FAKE_SUBSCRIPTION_CANCELED)

        event = self._create_event(FAKE_EVENT_CUSTOMER_SUBSCRIPTION_DELETED)
        event.invoke_webhook_handlers()

        sub = Subscription.objects.get(id=FAKE_SUBSCRIPTION["id"])
        # Check that Subscription is canceled and not deleted
        self.assertEqual(sub.status, SubscriptionStatus.canceled)
        self.assertIsNotNone(sub.canceled_at)

    @patch("stripe.Customer.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_customer_bogus_event_type(
        self, event_retrieve_mock, customer_retrieve_mock
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_CREATED)
        fake_stripe_event["data"]["object"]["customer"] = fake_stripe_event["data"][
            "object"
        ]["id"]
        fake_stripe_event["type"] = "customer.praised"

        event_retrieve_mock.return_value = fake_stripe_event
        customer_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()


class TestDisputeEvents(EventTestCase):
    def setUp(self):

        self.user = get_user_model().objects.create_user(
            username="fake_customer_1", email=FAKE_CUSTOMER["email"]
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_PAYMENT_INTENT),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_CHARGE),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_BALANCE_TRANSACTION),
    )
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Dispute.retrieve", return_value=deepcopy(FAKE_DISPUTE_I), autospec=True
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_DISPUTE_CREATED),
        autospec=True,
    )
    def test_dispute_created(
        self,
        event_retrieve_mock,
        dispute_retrieve_mock,
        file_retrieve_mock,
        balance_transaction_retrieve_mock,
        charge_retrieve_mock,
        payment_intent_retrieve_mock,
        payment_method_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_DISPUTE_CREATED)
        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()
        dispute = Dispute.objects.get()
        self.assertEqual(dispute.id, FAKE_DISPUTE_I["id"])

    # funds get withdrawn from the account as soon as a charge is
    # disputed so practically there is no difference between
    # charge.dispute.created and charge.dispute.funds_withdrawn
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_PAYMENT_INTENT),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_CHARGE),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_BALANCE_TRANSACTION),
    )
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Dispute.retrieve", return_value=deepcopy(FAKE_DISPUTE_II), autospec=True
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_DISPUTE_FUNDS_WITHDRAWN),
        autospec=True,
    )
    def test_dispute_funds_withdrawn(
        self,
        event_retrieve_mock,
        dispute_retrieve_mock,
        file_retrieve_mock,
        balance_transaction_retrieve_mock,
        charge_retrieve_mock,
        payment_intent_retrieve_mock,
        payment_method_retrieve_mock,
    ):

        fake_stripe_event = deepcopy(FAKE_EVENT_DISPUTE_FUNDS_WITHDRAWN)
        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()
        dispute = Dispute.objects.get()
        self.assertEqual(dispute.id, FAKE_DISPUTE_II["id"])

    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_PAYMENT_INTENT),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_CHARGE),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_BALANCE_TRANSACTION),
    )
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Dispute.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_III),
        autospec=True,
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_DISPUTE_UPDATED),
        autospec=True,
    )
    def test_dispute_updated(
        self,
        event_retrieve_mock,
        dispute_retrieve_mock,
        file_retrieve_mock,
        balance_transaction_retrieve_mock,
        charge_retrieve_mock,
        payment_intent_retrieve_mock,
        payment_method_retrieve_mock,
    ):

        fake_stripe_event = deepcopy(FAKE_EVENT_DISPUTE_UPDATED)
        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()
        dispute = Dispute.objects.get()
        self.assertEqual(dispute.id, FAKE_DISPUTE_III["id"])

    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_PAYMENT_INTENT),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_CHARGE),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_BALANCE_TRANSACTION),
    )
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Dispute.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_III),
        autospec=True,
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_DISPUTE_CLOSED),
        autospec=True,
    )
    def test_dispute_closed(
        self,
        event_retrieve_mock,
        dispute_retrieve_mock,
        file_retrieve_mock,
        balance_transaction_retrieve_mock,
        charge_retrieve_mock,
        payment_intent_retrieve_mock,
        payment_method_retrieve_mock,
    ):

        fake_stripe_event = deepcopy(FAKE_EVENT_DISPUTE_CLOSED)
        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()
        dispute = Dispute.objects.get()
        self.assertEqual(dispute.id, FAKE_DISPUTE_III["id"])

    # funds get reinstated after the dispute is closed
    # includes full fund reinstatements as well as partial refunds
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_PAYMENT_INTENT),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_CHARGE),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        side_effect=[
            FAKE_DISPUTE_BALANCE_TRANSACTION,
            FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_FULL,
        ],
    )
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Dispute.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_V_FULL),
        autospec=True,
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_DISPUTE_FUNDS_REINSTATED_FULL),
        autospec=True,
    )
    def test_dispute_funds_reinstated_full(
        self,
        event_retrieve_mock,
        dispute_retrieve_mock,
        file_retrieve_mock,
        balance_transaction_retrieve_mock,
        charge_retrieve_mock,
        payment_intent_retrieve_mock,
        payment_method_retrieve_mock,
    ):

        fake_stripe_event = deepcopy(FAKE_EVENT_DISPUTE_FUNDS_REINSTATED_FULL)
        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()
        dispute = Dispute.objects.get()
        self.assertEqual(dispute.id, FAKE_DISPUTE_V_FULL["id"])

    # funds get reinstated after the dispute is closed
    # includes full fund reinstatements as well as partial refunds
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_PAYMENT_INTENT),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_CHARGE),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        side_effect=[
            FAKE_DISPUTE_BALANCE_TRANSACTION,
            FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_PARTIAL,
        ],
    )
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Dispute.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_V_PARTIAL),
        autospec=True,
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_DISPUTE_FUNDS_REINSTATED_PARTIAL),
        autospec=True,
    )
    def test_dispute_funds_reinstated_partial(
        self,
        event_retrieve_mock,
        dispute_retrieve_mock,
        file_retrieve_mock,
        balance_transaction_retrieve_mock,
        charge_retrieve_mock,
        payment_intent_retrieve_mock,
        payment_method_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_DISPUTE_FUNDS_REINSTATED_PARTIAL)
        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()
        dispute = Dispute.objects.get()
        self.assertGreaterEqual(len(dispute.balance_transactions), 2)
        self.assertEqual(dispute.id, FAKE_DISPUTE_V_PARTIAL["id"])


class TestFileEvents(EventTestCase):
    def setUp(self):

        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_FILE_CREATED),
        autospec=True,
    )
    def test_file_created(self, event_retrieve_mock, file_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_FILE_CREATED)
        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()
        file = File.objects.get()
        self.assertEqual(file.id, FAKE_FILEUPLOAD_ICON["id"])


class TestInvoiceEvents(EventTestCase):
    def setUp(self):

        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
        autospec=True,
    )
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
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch("stripe.Event.retrieve", autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_invoice_created_no_existing_customer(
        self,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        event_retrieve_mock,
        invoice_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):

        fake_stripe_event = deepcopy(FAKE_EVENT_INVOICE_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event

        invoice_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        self.assertEqual(Customer.objects.count(), 1)
        customer = Customer.objects.get()
        self.assertEqual(customer.subscriber, None)

    @patch(
        "djstripe.models.Account.get_default_account",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
        autospec=True,
    )
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
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch("stripe.Invoice.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_invoice_created(
        self,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        event_retrieve_mock,
        invoice_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):

        FAKE_CUSTOMER.create_for_user(self.user)

        fake_stripe_event = deepcopy(FAKE_EVENT_INVOICE_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event

        invoice_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        invoice = Invoice.objects.get(id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(
            invoice.amount_due,
            fake_stripe_event["data"]["object"]["amount_due"] / Decimal("100"),
        )
        self.assertEqual(invoice.paid, fake_stripe_event["data"]["object"]["paid"])

    @patch(
        "djstripe.models.Account.get_default_account",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
        autospec=True,
    )
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
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_invoice_deleted(
        self,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        invoice_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):

        FAKE_CUSTOMER.create_for_user(self.user)

        event = self._create_event(FAKE_EVENT_INVOICE_CREATED)
        event.invoke_webhook_handlers()

        Invoice.objects.get(id=FAKE_INVOICE["id"])

        event = self._create_event(FAKE_EVENT_INVOICE_DELETED)
        event.invoke_webhook_handlers()

        with self.assertRaises(Invoice.DoesNotExist):
            Invoice.objects.get(id=FAKE_INVOICE["id"])

    def test_invoice_upcoming(self):
        # Ensure that invoice upcoming events are processed - No actual
        # process occurs so the operation is an effective no-op.
        event = self._create_event(FAKE_EVENT_INVOICE_UPCOMING)
        event.invoke_webhook_handlers()


class TestInvoiceItemEvents(EventTestCase):
    def setUp(self):

        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II), autospec=True
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_II),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II), autospec=True
    )
    @patch("stripe.InvoiceItem.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    def test_invoiceitem_created(
        self,
        customer_retrieve_mock,
        product_retrieve_mock,
        event_retrieve_mock,
        invoiceitem_retrieve_mock,
        invoice_retrieve_mock,
        paymentintent_retrieve_mock,
        paymentmethod_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):

        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_II)
        fake_payment_intent["invoice"] = FAKE_INVOICE_II["id"]
        paymentintent_retrieve_mock.return_value = fake_payment_intent

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION_III)
        fake_subscription["latest_invoice"] = FAKE_INVOICE_II["id"]
        subscription_retrieve_mock.return_value = fake_subscription

        fake_card = deepcopy(FAKE_CARD_II)
        fake_card["customer"] = None
        # create Card for FAKE_CUSTOMER_III
        Card.sync_from_stripe_data(fake_card)

        # create invoice
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE_II))

        FAKE_CUSTOMER_II.create_for_user(self.user)

        fake_stripe_event = deepcopy(FAKE_EVENT_INVOICEITEM_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event

        invoiceitem_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        invoiceitem = InvoiceItem.objects.get(
            id=fake_stripe_event["data"]["object"]["id"]
        )
        self.assertEqual(
            invoiceitem.amount,
            fake_stripe_event["data"]["object"]["amount"] / Decimal("100"),
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II), autospec=True
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_II),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II), autospec=True
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    def test_invoiceitem_deleted(
        self,
        customer_retrieve_mock,
        product_retrieve_mock,
        invoiceitem_retrieve_mock,
        invoice_retrieve_mock,
        paymentintent_retrieve_mock,
        paymentmethod_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_II)
        fake_payment_intent["invoice"] = FAKE_INVOICE_II["id"]
        paymentintent_retrieve_mock.return_value = fake_payment_intent

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION_III)
        fake_subscription["latest_invoice"] = FAKE_INVOICE_II["id"]
        subscription_retrieve_mock.return_value = fake_subscription

        fake_card = deepcopy(FAKE_CARD_II)
        fake_card["customer"] = None
        # create Card for FAKE_CUSTOMER_III
        Card.sync_from_stripe_data(fake_card)

        # create invoice
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE_II))

        FAKE_CUSTOMER_II.create_for_user(self.user)

        event = self._create_event(FAKE_EVENT_INVOICEITEM_CREATED)
        event.invoke_webhook_handlers()

        InvoiceItem.objects.get(id=FAKE_INVOICEITEM["id"])

        event = self._create_event(FAKE_EVENT_INVOICEITEM_DELETED)
        event.invoke_webhook_handlers()

        with self.assertRaises(InvoiceItem.DoesNotExist):
            InvoiceItem.objects.get(id=FAKE_INVOICEITEM["id"])


class TestPlanEvents(EventTestCase):
    @patch("stripe.Plan.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_plan_created(
        self, product_retrieve_mock, event_retrieve_mock, plan_retrieve_mock
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_PLAN_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event
        plan_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        plan = Plan.objects.get(id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(plan.nickname, fake_stripe_event["data"]["object"]["nickname"])

    @patch("stripe.Plan.retrieve", return_value=FAKE_PLAN, autospec=True)
    @patch(
        "stripe.Event.retrieve",
        return_value=FAKE_EVENT_PLAN_REQUEST_IS_OBJECT,
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_plan_updated_request_object(
        self, product_retrieve_mock, event_retrieve_mock, plan_retrieve_mock
    ):
        plan_retrieve_mock.return_value = FAKE_EVENT_PLAN_REQUEST_IS_OBJECT["data"][
            "object"
        ]

        event = Event.sync_from_stripe_data(FAKE_EVENT_PLAN_REQUEST_IS_OBJECT)
        event.invoke_webhook_handlers()

        plan = Plan.objects.get(
            id=FAKE_EVENT_PLAN_REQUEST_IS_OBJECT["data"]["object"]["id"]
        )
        self.assertEqual(
            plan.nickname,
            FAKE_EVENT_PLAN_REQUEST_IS_OBJECT["data"]["object"]["nickname"],
        )

    @patch("stripe.Plan.retrieve", return_value=FAKE_PLAN, autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_plan_deleted(self, product_retrieve_mock, plan_retrieve_mock):

        event = self._create_event(FAKE_EVENT_PLAN_CREATED)
        event.invoke_webhook_handlers()

        Plan.objects.get(id=FAKE_PLAN["id"])

        event = self._create_event(FAKE_EVENT_PLAN_DELETED)
        event.invoke_webhook_handlers()

        with self.assertRaises(Plan.DoesNotExist):
            Plan.objects.get(id=FAKE_PLAN["id"])


class TestPriceEvents(EventTestCase):
    @patch("stripe.Price.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_price_created(
        self, product_retrieve_mock, event_retrieve_mock, price_retrieve_mock
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_PRICE_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event
        price_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        price = Price.objects.get(id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(
            price.nickname, fake_stripe_event["data"]["object"]["nickname"]
        )

    @patch("stripe.Price.retrieve", return_value=FAKE_PRICE, autospec=True)
    @patch(
        "stripe.Event.retrieve", return_value=FAKE_EVENT_PRICE_UPDATED, autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_price_updated(
        self, product_retrieve_mock, event_retrieve_mock, price_retrieve_mock
    ):
        price_retrieve_mock.return_value = FAKE_EVENT_PRICE_UPDATED["data"]["object"]

        event = Event.sync_from_stripe_data(FAKE_EVENT_PRICE_UPDATED)
        event.invoke_webhook_handlers()

        price = Price.objects.get(id=FAKE_EVENT_PRICE_UPDATED["data"]["object"]["id"])
        self.assertEqual(
            price.unit_amount,
            FAKE_EVENT_PRICE_UPDATED["data"]["object"]["unit_amount"],
        )
        self.assertEqual(
            price.unit_amount_decimal,
            Decimal(FAKE_EVENT_PRICE_UPDATED["data"]["object"]["unit_amount_decimal"]),
        )

    @patch("stripe.Price.retrieve", return_value=FAKE_PRICE, autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_price_deleted(self, product_retrieve_mock, price_retrieve_mock):

        event = self._create_event(FAKE_EVENT_PRICE_CREATED)
        event.invoke_webhook_handlers()

        Price.objects.get(id=FAKE_PRICE["id"])

        event = self._create_event(FAKE_EVENT_PRICE_DELETED)
        event.invoke_webhook_handlers()

        with self.assertRaises(Price.DoesNotExist):
            Price.objects.get(id=FAKE_PRICE["id"])


class TestPaymentMethodEvents(AssertStripeFksMixin, EventTestCase):
    def setUp(self):

        self.user = get_user_model().objects.create_user(
            username="fake_customer_1", email=FAKE_CUSTOMER["email"]
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

    @patch("stripe.PaymentMethod.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_payment_method_attached(
        self, event_retrieve_mock, payment_method_retrieve_mock
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_PAYMENT_METHOD_ATTACHED)
        event_retrieve_mock.return_value = fake_stripe_event
        payment_method_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        payment_method = PaymentMethod.objects.get(
            id=fake_stripe_event["data"]["object"]["id"]
        )

        self.assert_fks(
            payment_method,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
            },
        )

    @patch("stripe.PaymentMethod.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_card_payment_method_attached(
        self, event_retrieve_mock, payment_method_retrieve_mock
    ):
        # Attach of a legacy id="card_xxx" payment method should behave exactly
        # as per a normal "native" id="pm_yyy" payment_method.
        fake_stripe_event = deepcopy(FAKE_EVENT_CARD_PAYMENT_METHOD_ATTACHED)
        event_retrieve_mock.return_value = fake_stripe_event
        payment_method_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        payment_method = PaymentMethod.objects.get(
            id=fake_stripe_event["data"]["object"]["id"]
        )

        self.assert_fks(
            payment_method,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
            },
        )

    @patch("stripe.PaymentMethod.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_payment_method_detached(
        self, event_retrieve_mock, payment_method_retrieve_mock
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_PAYMENT_METHOD_DETACHED)
        event_retrieve_mock.return_value = fake_stripe_event
        payment_method_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        payment_method = PaymentMethod.objects.get(
            id=fake_stripe_event["data"]["object"]["id"]
        )

        self.assertIsNone(
            payment_method.customer,
            "Detach of a payment_method should set customer to null",
        )

        self.assert_fks(
            payment_method, expected_blank_fks={"djstripe.PaymentMethod.customer"}
        )

    @patch(
        "stripe.PaymentMethod.retrieve",
        side_effect=InvalidRequestError(
            message="No such payment_method: card_xxxx",
            param="payment_method",
            code="resource_missing",
        ),
        autospec=True,
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_card_payment_method_detached(
        self, event_retrieve_mock, payment_method_retrieve_mock
    ):
        # Detach of a legacy id="card_xxx" payment method is handled specially,
        # since the card is deleted by Stripe and therefore PaymetMethod.retrieve fails

        fake_stripe_event = deepcopy(FAKE_EVENT_CARD_PAYMENT_METHOD_DETACHED)
        event_retrieve_mock.return_value = fake_stripe_event
        payment_method_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        self.assertEqual(
            PaymentMethod.objects.filter(
                id=fake_stripe_event["data"]["object"]["id"]
            ).count(),
            0,
            "Detach of a 'card_' payment_method should delete it",
        )


class TestPaymentIntentEvents(EventTestCase):
    """Test case for payment intent event handling."""

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.File.retrieve",
        side_effect=(deepcopy(FAKE_FILEUPLOAD_ICON), deepcopy(FAKE_FILEUPLOAD_LOGO)),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_DESTINATION_CHARGE),
        autospec=True,
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
        autospec=True,
    )
    def test_payment_intent_succeeded_with_destination_charge(
        self,
        customer_retrieve_mock,
        account_retrieve_mock,
        file_upload_retrieve_mock,
        payment_intent_retrieve_mock,
        payment_method_retrieve_mock,
    ):
        """Test that the payment intent succeeded event can create all related objects.

        This should exercise the machinery to set `stripe_account` when recursing into
        objects related to a connect `Account`.
        """
        event = self._create_event(
            FAKE_EVENT_PAYMENT_INTENT_SUCCEEDED_DESTINATION_CHARGE
        )
        event.invoke_webhook_handlers()

        # Make sure the file uploads were retrieved using the account ID.
        file_upload_retrieve_mock.assert_has_calls(
            (
                call(
                    id=FAKE_FILEUPLOAD_ICON["id"],
                    api_key=ANY,
                    expand=ANY,
                    stripe_account=FAKE_ACCOUNT["id"],
                ),
                call(
                    id=FAKE_FILEUPLOAD_LOGO["id"],
                    api_key=ANY,
                    expand=ANY,
                    stripe_account=FAKE_ACCOUNT["id"],
                ),
            )
        )


class TestSubscriptionScheduleEvents(EventTestCase):
    @patch(
        "stripe.SubscriptionSchedule.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    def test_subscription_schedule_created(
        self,
        customer_retrieve_mock,
        schedule_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED)
        fake_stripe_event["data"]["object"]["subscription"] = None

        fake_subscription_schedule = deepcopy(FAKE_SUBSCRIPTION_SCHEDULE)
        fake_subscription_schedule["subscription"] = None
        schedule_retrieve_mock.return_value = fake_subscription_schedule

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        schedule = SubscriptionSchedule.objects.get(
            id=fake_stripe_event["data"]["object"]["id"]
        )

        assert schedule.id == fake_stripe_event["data"]["object"]["id"]
        assert schedule.status == "not_started"

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
    @patch(
        "stripe.SubscriptionSchedule.retrieve",
        return_value=FAKE_SUBSCRIPTION_SCHEDULE,
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    def test_subscription_schedule_and_subscription_created(
        self,
        customer_retrieve_mock,
        schedule_retrieve_mock,
        invoice_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        # create latest invoice
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        event = Event.sync_from_stripe_data(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED)
        event.invoke_webhook_handlers()

        schedule = SubscriptionSchedule.objects.get(
            id=FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED["data"]["object"]["id"]
        )

        assert (
            schedule.id
            == FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED["data"]["object"]["id"]
        )
        assert schedule.status == "not_started"

    @patch("stripe.SubscriptionSchedule.retrieve", autospec=True)
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    def test_subscription_schedule_canceled(
        self, customer_retrieve_mock, schedule_retrieve_mock
    ):

        fake_stripe_event = deepcopy(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_UPDATED)
        fake_stripe_event["data"]["previous_attributes"] = {
            "canceled_at": None,
            "status": "not_started",
        }
        fake_stripe_event["data"]["object"]["subscription"] = None

        fake_subscription_schedule = deepcopy(FAKE_SUBSCRIPTION_SCHEDULE)
        fake_subscription_schedule["subscription"] = None
        fake_subscription_schedule["canceled_at"] = 1605058030
        fake_subscription_schedule["status"] = "canceled"
        schedule_retrieve_mock.return_value = fake_subscription_schedule

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        schedule = SubscriptionSchedule.objects.get(
            id=fake_stripe_event["data"]["object"]["id"]
        )

        assert schedule.status == "canceled"
        assert schedule.canceled_at is not None

        fake_stripe_event_2 = deepcopy(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CANCELED)
        fake_stripe_event_2["data"]["object"]["subscription"] = None

        schedule_retrieve_mock.return_value = fake_stripe_event_2["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event_2)
        event.invoke_webhook_handlers()

        schedule.refresh_from_db()

        assert schedule.status == "canceled"
        assert schedule.canceled_at is not None

    @patch("stripe.SubscriptionSchedule.retrieve", autospec=True)
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    def test_subscription_schedule_completed(
        self, customer_retrieve_mock, schedule_retrieve_mock
    ):

        fake_stripe_event = deepcopy(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_UPDATED)
        fake_stripe_event["data"]["object"]["subscription"] = None

        fake_subscription_schedule = deepcopy(FAKE_SUBSCRIPTION_SCHEDULE)
        fake_subscription_schedule["subscription"] = None
        fake_subscription_schedule["completed_at"] = 1605058030
        fake_subscription_schedule["status"] = "completed"
        schedule_retrieve_mock.return_value = fake_subscription_schedule

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        schedule = SubscriptionSchedule.objects.get(
            id=fake_stripe_event["data"]["object"]["id"]
        )

        assert schedule.status == "completed"
        assert schedule.completed_at is not None

        fake_stripe_event_2 = deepcopy(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_COMPLETED)
        fake_stripe_event_2["data"]["object"]["subscription"] = None

        schedule_retrieve_mock.return_value = fake_stripe_event_2["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event_2)
        event.invoke_webhook_handlers()

        schedule.refresh_from_db()

        assert schedule.status == "completed"
        assert schedule.completed_at is not None

    @patch("stripe.SubscriptionSchedule.retrieve", autospec=True)
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    def test_subscription_schedule_expiring(
        self, customer_retrieve_mock, schedule_retrieve_mock
    ):

        fake_stripe_event = deepcopy(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_UPDATED)
        fake_stripe_event["data"]["object"]["subscription"] = None

        fake_subscription_schedule = deepcopy(FAKE_SUBSCRIPTION_SCHEDULE)
        fake_subscription_schedule["subscription"] = None
        fake_subscription_schedule["status"] = "active"
        schedule_retrieve_mock.return_value = fake_subscription_schedule

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        schedule = SubscriptionSchedule.objects.get(
            id=fake_stripe_event["data"]["object"]["id"]
        )

        assert schedule.status == "active"
        assert schedule.completed_at is None

        fake_stripe_event_2 = deepcopy(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_EXPIRING)
        fake_stripe_event_2["data"]["object"]["subscription"] = None

        schedule_retrieve_mock.return_value = fake_stripe_event_2["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event_2)
        event.invoke_webhook_handlers()

        schedule.refresh_from_db()

        assert schedule.status == "active"
        assert schedule.completed_at is None

    @patch("stripe.SubscriptionSchedule.retrieve", autospec=True)
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    def test_subscription_schedule_released(
        self, customer_retrieve_mock, schedule_retrieve_mock
    ):

        fake_stripe_event = deepcopy(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_UPDATED)
        fake_stripe_event["data"]["previous_attributes"] = {
            "released_at": None,
            "status": "not_started",
        }
        fake_stripe_event["data"]["object"]["subscription"] = None

        fake_subscription_schedule = deepcopy(FAKE_SUBSCRIPTION_SCHEDULE)
        fake_subscription_schedule["subscription"] = None
        fake_subscription_schedule["released_at"] = 1605058030
        fake_subscription_schedule["status"] = "released"
        schedule_retrieve_mock.return_value = fake_subscription_schedule

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        schedule = SubscriptionSchedule.objects.get(
            id=fake_stripe_event["data"]["object"]["id"]
        )

        assert schedule.status == "released"
        assert schedule.released_at is not None

        fake_stripe_event_2 = deepcopy(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_RELEASED)
        fake_stripe_event_2["data"]["object"]["subscription"] = None

        schedule_retrieve_mock.return_value = fake_stripe_event_2["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event_2)
        event.invoke_webhook_handlers()

        schedule.refresh_from_db()

        assert schedule.status == "released"
        assert schedule.released_at is not None

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
    @patch("stripe.SubscriptionSchedule.retrieve", autospec=True)
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    def test_subscription_schedule_updated(
        self,
        customer_retrieve_mock,
        schedule_retrieve_mock,
        invoice_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED)
        fake_stripe_event["data"]["object"]["subscription"] = None

        fake_subscription_schedule = deepcopy(FAKE_SUBSCRIPTION_SCHEDULE)
        schedule_retrieve_mock.return_value = fake_subscription_schedule

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        schedule = SubscriptionSchedule.objects.get(
            id=fake_stripe_event["data"]["object"]["id"]
        )

        assert schedule.released_at is None

        fake_stripe_event = deepcopy(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_UPDATED)
        fake_stripe_event["data"]["object"]["released_at"] = 1605058030
        fake_stripe_event["data"]["object"]["status"] = "released"
        fake_stripe_event["data"]["previous_attributes"] = {
            "released_at": None,
            "status": "not_started",
        }

        schedule_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        schedule = SubscriptionSchedule.objects.get(
            id=fake_stripe_event["data"]["object"]["id"]
        )

        assert schedule.status == "released"
        assert schedule.released_at is not None

    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
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
    @patch(
        "stripe.SubscriptionSchedule.retrieve",
        return_value=FAKE_SUBSCRIPTION_SCHEDULE,
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    def test_subscription_schedule_aborted(
        self,
        customer_retrieve_mock,
        schedule_retrieve_mock,
        invoice_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_subscription = deepcopy(FAKE_SUBSCRIPTION)
        subscription_retrieve_mock.return_value = fake_subscription

        # create latest invoice (and the associated subscription)
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        event = Event.sync_from_stripe_data(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED)
        event.invoke_webhook_handlers()

        schedule = SubscriptionSchedule.objects.get(
            id=FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED["data"]["object"]["id"]
        )

        assert (
            schedule.id
            == FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED["data"]["object"]["id"]
        )

        assert schedule.subscription.id == FAKE_SUBSCRIPTION["id"]
        assert schedule.subscription.status == "active"

        # cancel the subscription
        fake_subscription["status"] = "canceled"
        Subscription.sync_from_stripe_data(fake_subscription)

        fake_stripe_event_2 = deepcopy(FAKE_EVENT_SUBSCRIPTION_SCHEDULE_ABORTED)
        schedule_retrieve_mock.return_value = fake_stripe_event_2["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event_2)
        event.invoke_webhook_handlers()

        schedule.refresh_from_db()

        assert schedule.status == "canceled"
        assert schedule.subscription.status == "canceled"
        assert schedule.canceled_at is not None


class TestTaxIdEvents(EventTestCase):
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve_tax_id",
        return_value=deepcopy(FAKE_TAX_ID),
        autospec=True,
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_TAX_ID_CREATED),
        autospec=True,
    )
    def test_tax_id_created(
        self, event_retrieve_mock, tax_id_retrieve_mock, customer_retrieve_mock
    ):
        event = Event.sync_from_stripe_data(FAKE_EVENT_TAX_ID_CREATED)
        event.invoke_webhook_handlers()
        tax_id = TaxId.objects.get()
        self.assertEqual(tax_id.id, FAKE_TAX_ID["id"])

    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve_tax_id",
        autospec=True,
    )
    @patch(
        "stripe.Event.retrieve",
        autospec=True,
    )
    def test_tax_id_updated(
        self, event_retrieve_mock, tax_id_retrieve_mock, customer_retrieve_mock
    ):
        tax_id_retrieve_mock.return_value = FAKE_TAX_ID

        fake_stripe_create_event = deepcopy(FAKE_EVENT_TAX_ID_CREATED)
        event = Event.sync_from_stripe_data(fake_stripe_create_event)
        event.invoke_webhook_handlers()

        tax_id_retrieve_mock.return_value = FAKE_TAX_ID_UPDATED
        fake_stripe_update_event = deepcopy(FAKE_EVENT_TAX_ID_UPDATED)
        event = Event.sync_from_stripe_data(fake_stripe_update_event)
        event.invoke_webhook_handlers()

        tax_id = TaxId.objects.get()
        self.assertEqual(tax_id.id, FAKE_TAX_ID["id"])
        self.assertEqual(tax_id.verification.get("status"), "verified")
        self.assertEqual(tax_id.verification.get("verified_name"), "Test")

    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve_tax_id",
        autospec=True,
    )
    @patch(
        "stripe.Event.retrieve",
        autospec=True,
    )
    def test_tax_id_deleted(
        self, event_retrieve_mock, tax_id_retrieve_mock, customer_retrieve_mock
    ):
        tax_id_retrieve_mock.return_value = FAKE_TAX_ID

        fake_stripe_create_event = deepcopy(FAKE_EVENT_TAX_ID_CREATED)
        event = Event.sync_from_stripe_data(fake_stripe_create_event)
        event.invoke_webhook_handlers()

        tax_id_retrieve_mock.return_value = FAKE_EVENT_TAX_ID_DELETED
        fake_stripe_delete_event = deepcopy(FAKE_EVENT_TAX_ID_DELETED)
        event = Event.sync_from_stripe_data(fake_stripe_delete_event)
        event.invoke_webhook_handlers()

        self.assertFalse(TaxId.objects.filter(id=FAKE_TAX_ID["id"]).exists())


class TestTransferEvents(EventTestCase):
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
        autospec=True,
    )
    @patch("stripe.Transfer.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_transfer_created(
        self,
        event_retrieve_mock,
        transfer_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event
        transfer_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        transfer = Transfer.objects.get(id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(
            transfer.amount,
            fake_stripe_event["data"]["object"]["amount"] / Decimal("100"),
        )

    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
        autospec=True,
    )
    @patch("stripe.Transfer.retrieve", return_value=FAKE_TRANSFER, autospec=True)
    def test_transfer_deleted(
        self,
        transfer_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)
        event.invoke_webhook_handlers()

        Transfer.objects.get(id=FAKE_TRANSFER["id"])

        event = self._create_event(FAKE_EVENT_TRANSFER_DELETED)
        event.invoke_webhook_handlers()

        with self.assertRaises(Transfer.DoesNotExist):
            Transfer.objects.get(id=FAKE_TRANSFER["id"])

        event = self._create_event(FAKE_EVENT_TRANSFER_DELETED)
        event.invoke_webhook_handlers()


class TestOrderEvents(EventTestCase):
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
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
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
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch("stripe.Order.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_order_created(
        self,
        event_retrieve_mock,
        order_retrieve_mock,
        invoice_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_ORDER_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event
        order_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        order = Order.objects.get(id=fake_stripe_event["data"]["object"]["id"])

        self.assertEqual(order.status, "open")
        self.assertEqual(order.payment_intent, None)
        self.assertEqual(order.customer.id, FAKE_CUSTOMER["id"])

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
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
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
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch("stripe.Order.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_order_updated(
        self,
        event_retrieve_mock,
        order_retrieve_mock,
        invoice_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_ORDER_UPDATED)
        event_retrieve_mock.return_value = fake_stripe_event
        order_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        order = Order.objects.get(id=fake_stripe_event["data"]["object"]["id"])

        # assert email got updated
        self.assertEqual(order.billing_details["email"], "arnav13@gmail.com")
        self.assertEqual(order.payment_intent.id, FAKE_PAYMENT_INTENT_I["id"])
        self.assertEqual(order.customer.id, FAKE_CUSTOMER["id"])

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
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
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
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch("stripe.Order.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_order_submitted(
        self,
        event_retrieve_mock,
        order_retrieve_mock,
        invoice_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_ORDER_SUBMITTED)
        event_retrieve_mock.return_value = fake_stripe_event
        order_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        order = Order.objects.get(id=fake_stripe_event["data"]["object"]["id"])

        self.assertEqual(order.status, "submitted")
        self.assertEqual(order.billing_details["email"], "arnav13@gmail.com")
        self.assertEqual(order.payment_intent.id, FAKE_PAYMENT_INTENT_I["id"])
        self.assertEqual(order.customer.id, FAKE_CUSTOMER["id"])

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
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
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
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch("stripe.Order.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_order_processing(
        self,
        event_retrieve_mock,
        order_retrieve_mock,
        invoice_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_ORDER_PROCESSING)
        event_retrieve_mock.return_value = fake_stripe_event
        order_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        order = Order.objects.get(id=fake_stripe_event["data"]["object"]["id"])

        self.assertEqual(order.status, "processing")
        self.assertEqual(order.billing_details["email"], "arnav13@gmail.com")
        self.assertEqual(order.payment_intent.id, FAKE_PAYMENT_INTENT_I["id"])
        self.assertEqual(order.customer.id, FAKE_CUSTOMER["id"])

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
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
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
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch("stripe.Order.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_order_cancelled(
        self,
        event_retrieve_mock,
        order_retrieve_mock,
        invoice_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_ORDER_CANCELLED)
        event_retrieve_mock.return_value = fake_stripe_event
        order_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        order = Order.objects.get(id=fake_stripe_event["data"]["object"]["id"])

        self.assertEqual(order.status, "canceled")
        self.assertEqual(order.billing_details["email"], "arnav13@gmail.com")
        self.assertEqual(order.payment_intent.id, FAKE_PAYMENT_INTENT_I["id"])
        self.assertEqual(order.customer.id, FAKE_CUSTOMER["id"])

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
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
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
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch("stripe.Order.retrieve", autospec=True)
    @patch("stripe.Event.retrieve", autospec=True)
    def test_order_complet(
        self,
        event_retrieve_mock,
        order_retrieve_mock,
        invoice_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_stripe_event = deepcopy(FAKE_EVENT_ORDER_COMPLETED)
        event_retrieve_mock.return_value = fake_stripe_event
        order_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.invoke_webhook_handlers()

        order = Order.objects.get(id=fake_stripe_event["data"]["object"]["id"])

        self.assertEqual(order.status, "complete")
        self.assertEqual(order.billing_details["email"], "arnav13@gmail.com")
        self.assertEqual(order.payment_intent.id, FAKE_PAYMENT_INTENT_I["id"])
        self.assertEqual(order.customer.id, FAKE_CUSTOMER["id"])
