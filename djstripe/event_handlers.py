"""
Webhook event handlers for the various models
Stripe docs for Events: https://stripe.com/docs/api/events
Stripe docs for Webhooks: https://stripe.com/docs/webhooks
TODO: Implement webhook event handlers for all the models that need to
      respond to webhook events.
NOTE:
    Event data is not guaranteed to be in the correct API version format.
    See #116. When writing a webhook handler, make sure to first
    re-retrieve the object you wish to process.
"""

import logging
from enum import Enum

from django.core.exceptions import ObjectDoesNotExist
from django.dispatch import receiver

from djstripe.models import Event
from djstripe.settings import djstripe_settings

from . import models
from .enums import PayoutType
from .signals import WEBHOOK_SIGNALS

logger = logging.getLogger(__name__)


def update_customer_helper(metadata, customer_id, subscriber_key):
    """
    A helper function that updates customer's subscriber and metadata fields
    """

    # only update customer.subscriber if both the customer and subscriber already exist
    subscriber_id = metadata.get(subscriber_key, "")
    if subscriber_key not in ("", None) and subscriber_id and customer_id:
        subscriber_model = djstripe_settings.get_subscriber_model()

        try:
            subscriber = subscriber_model.objects.get(id=subscriber_id)
            customer = models.Customer.objects.get(id=customer_id)
        except ObjectDoesNotExist:
            pass
        else:
            customer.subscriber = subscriber
            customer.metadata = metadata
            customer.save()


def djstripe_receiver(signal_names):
    """
    A wrapper around django's receiver to do some error checking.

    Ultimately connects event handlers to Django signals.

    Usage:
    Apply this decorator to a function, providing the 'signal_names.'
    It connects the function to the specified signal if 'signal_name' is enabled.

    Parameters:
    - signal_names (list or tuple or str): List or tuple of event names or just the event name itself.

    Example:
    @djstripe_receiver("my_signal")
    def my_event_handler(sender, event, **kwargs):
        # Custom event handling logic here

    @djstripe_receiver(["my_signal_1", "my_signal_2"])
    def my_event_handler(sender, event, **kwargs):
        # Custom event handling logic here

    """

    def _check_signal_exists(signal_name):
        """Helper function to make sure user does not register any event we do not yet support."""
        signal = WEBHOOK_SIGNALS.get(signal_name)
        if not signal:
            raise RuntimeError(
                f"Event '{signal_name}' is not enabled. This is a dj-stripe bug! Please raise a ticket and our maintainers will get right to it."
            )
        return signal

    signals = []
    if isinstance(signal_names, (list, tuple)):
        for signal_name in signal_names:
            signals.append(_check_signal_exists(signal_name))
    else:
        signals.append(_check_signal_exists(signal_names))

    def inner(handler, **kwargs):
        """
        Connectes the given handler to the given signal
        """
        # same as decorating the handler with receiver
        handler = receiver(signals, sender=Event, **kwargs)(handler)
        return handler

    return inner


@djstripe_receiver(["customer.created", "customer.updated", "customer.deleted"])
def handle_customer_event(sender, event, **kwargs):
    """Handle updates to customer objects.

    First determines the crud_type and then handles the event if a customer
    exists locally.
    As customers are tied to local users, djstripe will not create customers that
    do not already exist locally.

    And updates to the subscriber model and metadata fields of customer if present
    in checkout.sessions metadata key.

    Docs and an example customer webhook response:
    https://stripe.com/docs/api#customer_object
    """
    # will recieve all events of the type customer.X.Y so
    # need to ensure the data object is related to Customer Object
    target_object_type = event.data.get("object", {}).get("object", {})

    if event.customer and target_object_type == "customer":
        metadata = event.data.get("object", {}).get("metadata", {})
        customer_id = event.data.get("object", {}).get("id", "")
        subscriber_key = djstripe_settings.SUBSCRIBER_CUSTOMER_KEY
        # only update customer.subscriber if both the customer and subscriber already exist
        update_customer_helper(metadata, customer_id, subscriber_key)

        _handle_crud_like_event(target_cls=models.Customer, event=event)


@djstripe_receiver("customer.subscription.created")
@djstripe_receiver("customer.subscription.deleted")
@djstripe_receiver("customer.subscription.paused")
@djstripe_receiver("customer.subscription.pending_update_applied")
@djstripe_receiver("customer.subscription.pending_update_expired")
@djstripe_receiver("customer.subscription.resumed")
@djstripe_receiver("customer.subscription.trial_will_end")
@djstripe_receiver("customer.subscription.updated")
def handle_customer_subscription_event(sender, event, **kwargs):
    """Handle updates to customer subscription objects.

    Docs an example subscription webhook response:
    https://stripe.com/docs/api#subscription_object
    """

    # customer.subscription.deleted doesn't actually delete the subscription
    # on the stripe side, it updates it to canceled status, so override
    # crud_type to update to match.
    crud_type = CrudType.determine(event=event)
    if crud_type is CrudType.DELETED:
        crud_type = CrudType.UPDATED
    _handle_crud_like_event(
        target_cls=models.Subscription, event=event, crud_type=crud_type
    )


@djstripe_receiver("customer.tax_id.created")
@djstripe_receiver("customer.tax_id.deleted")
@djstripe_receiver("customer.tax_id.updated")
def handle_customer_tax_id_event(sender, event, **kwargs):
    """
    Handle updates to customer tax ID objects.
    """
    _handle_crud_like_event(
        target_cls=models.TaxId, event=event, crud_type=CrudType.determine(event=event)
    )


@djstripe_receiver("identity.verification_session.canceled")
@djstripe_receiver("identity.verification_session.created")
@djstripe_receiver("identity.verification_session.processing")
@djstripe_receiver("identity.verification_session.redacted")
@djstripe_receiver("identity.verification_session.requires_input")
@djstripe_receiver("identity.verification_session.verified")
def handle_identity_verification_session_event(sender, event, **kwargs):
    """
    Handle updates to Stripe Identity Verification Session objects.

    Docs: https://stripe.com/docs/api/identity/verification_sessions
    """
    _handle_crud_like_event(target_cls=models.VerificationSession, event=event)


@djstripe_receiver("payment_method.attached")
@djstripe_receiver("payment_method.automatically_updated")
@djstripe_receiver("payment_method.detached")
@djstripe_receiver("payment_method.updated")
def handle_payment_method_event(sender, event, **kwargs):
    """
    Handle updates to payment_method objects
    :param event:
    :return:

    Docs for:
    - payment_method: https://stripe.com/docs/api/payment_methods
    """
    # will recieve all events of the type payment_method.X.Y so
    # need to ensure the data object is related to PaymentMethod Object
    target_object_type = event.data.get("object", {}).get("object", {})

    if target_object_type == "payment_method":
        id_ = event.data.get("object", {}).get("id", None)

        if (
            event.parts == ["payment_method", "detached"]
            and id_
            and id_.startswith("card_")
        ):
            # Special case to handle a quirk in stripe's wrapping of legacy "card" objects
            # with payment_methods - card objects are deleted on detach, so treat this as
            # a delete event
            _handle_crud_like_event(
                target_cls=models.PaymentMethod,
                event=event,
                crud_type=CrudType.DELETED,
            )
        else:
            _handle_crud_like_event(target_cls=models.PaymentMethod, event=event)


@djstripe_receiver("account.external_account.created")
@djstripe_receiver("account.external_account.deleted")
@djstripe_receiver("account.external_account.updated")
def handle_account_external_account_event(sender, event, **kwargs):
    """
    Handles updates to Connected Accounts External Accounts
    """
    source_type = event.data.get("object", {}).get("object")
    if source_type == PayoutType.card:
        _handle_crud_like_event(target_cls=models.Card, event=event)

    if source_type == PayoutType.bank_account:
        _handle_crud_like_event(target_cls=models.BankAccount, event=event)


@djstripe_receiver("account.updated")
def handle_account_updated_event(sender, event, **kwargs):
    """
    Handles updates to Connected Accounts
        - account: https://stripe.com/docs/api/accounts
    """
    _handle_crud_like_event(
        target_cls=models.Account,
        event=event,
        crud_type=CrudType.UPDATED,
    )


@djstripe_receiver("charge.captured")
@djstripe_receiver("charge.expired")
@djstripe_receiver("charge.failed")
@djstripe_receiver("charge.pending")
@djstripe_receiver("charge.refund.updated")
@djstripe_receiver("charge.refunded")
@djstripe_receiver("charge.succeeded")
@djstripe_receiver("charge.updated")
def handle_charge_event(sender, event, **kwargs):
    """Handle updates to Charge objects
    - charge: https://stripe.com/docs/api/charges
    """
    # will recieve all events of the type charge.X.Y so
    # need to ensure the data object is related to Charge Object
    target_object_type = event.data.get("object", {}).get("object", {})

    if target_object_type == "charge":
        _handle_crud_like_event(target_cls=models.Charge, event=event)


@djstripe_receiver("charge.dispute.closed")
@djstripe_receiver("charge.dispute.created")
@djstripe_receiver("charge.dispute.funds_reinstated")
@djstripe_receiver("charge.dispute.funds_withdrawn")
@djstripe_receiver("charge.dispute.updated")
def handle_charge_dispute_event(sender, event, **kwargs):
    """Handle updates to Dispute objects
    - dispute: https://stripe.com/docs/api/disputes
    """
    # will recieve all events of the type charge.dispute.Y so
    # need to ensure the data object is related to Dispute Object
    target_object_type = event.data.get("object", {}).get("object", {})

    if target_object_type == "dispute":
        _handle_crud_like_event(target_cls=models.Dispute, event=event)


@djstripe_receiver("checkout.session.async_payment_failed")
@djstripe_receiver("checkout.session.async_payment_succeeded")
@djstripe_receiver("checkout.session.completed")
@djstripe_receiver("checkout.session.expired")
@djstripe_receiver("coupon.created")
@djstripe_receiver("coupon.deleted")
@djstripe_receiver("coupon.updated")
@djstripe_receiver("file.created")
@djstripe_receiver("invoice.created")
@djstripe_receiver("invoice.deleted")
@djstripe_receiver("invoice.finalization_failed")
@djstripe_receiver("invoice.finalized")
@djstripe_receiver("invoice.marked_uncollectible")
@djstripe_receiver("invoice.paid")
@djstripe_receiver("invoice.payment_action_required")
@djstripe_receiver("invoice.payment_failed")
@djstripe_receiver("invoice.payment_succeeded")
@djstripe_receiver("invoice.sent")
@djstripe_receiver("invoice.upcoming")
@djstripe_receiver("invoice.updated")
@djstripe_receiver("invoice.voided")
@djstripe_receiver("invoiceitem.created")
@djstripe_receiver("invoiceitem.deleted")
@djstripe_receiver("payment_intent.amount_capturable_updated")
@djstripe_receiver("payment_intent.canceled")
@djstripe_receiver("payment_intent.created")
@djstripe_receiver("payment_intent.partially_funded")
@djstripe_receiver("payment_intent.payment_failed")
@djstripe_receiver("payment_intent.processing")
@djstripe_receiver("payment_intent.requires_action")
@djstripe_receiver("payment_intent.succeeded")
@djstripe_receiver("payout.canceled")
@djstripe_receiver("payout.created")
@djstripe_receiver("payout.failed")
@djstripe_receiver("payout.paid")
@djstripe_receiver("payout.reconciliation_completed")
@djstripe_receiver("payout.updated")
@djstripe_receiver("price.created")
@djstripe_receiver("price.deleted")
@djstripe_receiver("price.updated")
@djstripe_receiver("product.created")
@djstripe_receiver("product.deleted")
@djstripe_receiver("product.updated")
@djstripe_receiver("setup_intent.canceled")
@djstripe_receiver("setup_intent.created")
@djstripe_receiver("setup_intent.requires_action")
@djstripe_receiver("setup_intent.setup_failed")
@djstripe_receiver("setup_intent.succeeded")
@djstripe_receiver("subscription_schedule.aborted")
@djstripe_receiver("subscription_schedule.canceled")
@djstripe_receiver("subscription_schedule.completed")
@djstripe_receiver("subscription_schedule.created")
@djstripe_receiver("subscription_schedule.expiring")
@djstripe_receiver("subscription_schedule.released")
@djstripe_receiver("subscription_schedule.updated")
@djstripe_receiver("tax_rate.created")
@djstripe_receiver("tax_rate.updated")
@djstripe_receiver("transfer.created")
@djstripe_receiver("transfer.reversed")
@djstripe_receiver("transfer.updated")
@djstripe_receiver("promotion_code.created")
@djstripe_receiver("promotion_code.updated")
def handle_other_event(sender, event, **kwargs):
    """
    Handle updates to checkout, coupon, file, invoice, invoiceitem, payment_intent,
    plan, product, setup_intent, subscription_schedule, tax_rate, promotion_code
    and transfer objects.

    Docs for:
    - checkout: https://stripe.com/docs/api/checkout/sessions
    - coupon: https://stripe.com/docs/api/coupons
    - file: https://stripe.com/docs/api/files
    - invoice: https://stripe.com/docs/api/invoices
    - invoiceitem: https://stripe.com/docs/api/invoiceitems
    - order: https://stripe.com/docs/api/orders_v2
    - payment_intent: https://stripe.com/docs/api/payment_intents
    - payout: https://stripe.com/docs/api/payouts
    - price: https://stripe.com/docs/api/prices
    - product: https://stripe.com/docs/api/products
    - setup_intent: https://stripe.com/docs/api/setup_intents
    - subscription_schedule: https://stripe.com/docs/api/subscription_schedules
    - tax_rate: https://stripe.com/docs/api/tax_rates/
    - transfer: https://stripe.com/docs/api/transfers
    - promotion_code: https://docs.stripe.com/api/promotion_codes
    """

    target_cls = {
        "checkout": models.Session,
        "coupon": models.Coupon,
        "file": models.File,
        "invoice": models.Invoice,
        "invoiceitem": models.InvoiceItem,
        "payment_intent": models.PaymentIntent,
        "payout": models.Payout,
        "price": models.Price,
        "product": models.Product,
        "transfer": models.Transfer,
        "setup_intent": models.SetupIntent,
        "subscription_schedule": models.SubscriptionSchedule,
        "tax_rate": models.TaxRate,
        "promotion_code": models.PromotionCode,
    }.get(event.category)

    _handle_crud_like_event(target_cls=target_cls, event=event)


#
# Helpers
#


class CrudType(Enum):
    """Helper object to determine CRUD-like event state."""

    UPDATED = "updated"
    DELETED = "deleted"

    @classmethod
    def determine(cls, event, verb=None):
        """
        Determine if the event verb is a crud_type (without the 'R') event.

        :param event:
        :type event: models.Event
        :param verb: The event verb to examine.
        :type verb: str
        :returns: The CrudType state object.
        :rtype: CrudType
        """
        verb = verb or event.verb

        for enum in CrudType:
            if verb.endswith(enum.value):
                return enum


def _handle_crud_like_event(
    target_cls, event: "models.Event", data=None, id: str | None = None, crud_type=None
):
    """
    Helper to process crud_type-like events for objects.

    Non-deletes (creates, updates and "anything else" events) are treated as
    update_or_create events - The object will be retrieved locally, then it is
    synchronised with the Stripe API for parity.

    Deletes only occur for delete events and cause the object to be deleted
    from the local database, if it existed.  If it doesn't exist then it is
    ignored (but the event processing still succeeds).

    :param target_cls: The djstripe model being handled.
    :type target_cls: Type[models.StripeModel]
    :param event: The event object
    :param data: The event object data (defaults to ``event.data``).
    :param id: The object Stripe ID (defaults to ``object.id``).
    :param crud_type: The CrudType object (determined by default).
    :returns: The object (if any) and the event CrudType.
    :rtype: Tuple[models.StripeModel, CrudType]
    """
    data = data or event.data
    id = id or data.get("object", {}).get("id", None)
    stripe_account = getattr(event.djstripe_owner_account, "id", None)

    if not id:
        # We require an object when applying CRUD-like events, so if there's
        # no ID the event is ignored/dropped. This happens in events such as
        # invoice.upcoming, which refer to a future (non-existant) invoice.
        logger.debug("Ignoring Stripe event %r without object ID", event.id)
        return

    crud_type = crud_type or CrudType.determine(event=event, verb=event.verb)

    if crud_type is CrudType.DELETED:
        qs = target_cls.objects.filter(id=id)
        if target_cls is models.Customer and qs.exists():
            qs.get().purge()
            obj = None
        else:
            obj = target_cls.objects.filter(id=id).delete()
    else:
        # Any other event type (creates, updates, etc.) - This can apply to
        # verbs that aren't strictly CRUD but Stripe do intend an update.  Such
        # as invoice.payment_failed.
        kwargs = {"id": id}
        if hasattr(target_cls, "customer"):
            kwargs["customer"] = event.customer

        # For account.external_account.* events
        if event.parts[:2] == ["account", "external_account"] and stripe_account:
            kwargs["account"] = models.Account._get_or_retrieve(id=stripe_account)

        # Stripe doesn't allow direct retrieval of Discount Objects
        if target_cls != models.Discount:
            data = target_cls(**kwargs).api_retrieve(
                stripe_account=stripe_account, api_key=event.default_api_key
            )
        else:
            data = data.get("object")

        # create or update the object from the retrieved Stripe Data
        obj = target_cls.sync_from_stripe_data(data, api_key=event.default_api_key)

    return obj


@djstripe_receiver("entitlements.active_entitlement_summary.updated")
def handle_customer_entitlements_event(sender, event, **kwargs):
    """
    Handle entitlements.active_entitlement_summary.updated events.

    This event tracks changes to a customer's active entitlements. We sync the
    Customer object to update the entitlements data stored in stripe_data.
    """
    object = event.data["object"]
    customer_id = object.get("customer")

    if not customer_id or not isinstance(customer_id, str):
        logger.debug(f"Ignoring malformed event id {event.id!r}")
        return

    # Check if customer exists locally - we don't create customers that don't exist
    if not models.Customer.objects.filter(id=customer_id).exists():
        logger.warning(
            f"Discarding event {event.id!r} because customer {customer_id!r} does not exist"
        )
        return

    # Use standard CRUD handler to retrieve and sync the full Customer
    _handle_crud_like_event(
        target_cls=models.Customer,
        event=event,
        id=customer_id,
        crud_type=CrudType.UPDATED,
    )
