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

from djstripe.settings import djstripe_settings

from . import models, webhooks
from .enums import PayoutType, SourceType
from .utils import convert_tstamp

logger = logging.getLogger(__name__)


def update_customer_helper(metadata, customer_id, subscriber_key):
    """
    A helper function that updates customer's subscriber and metadata fields
    """

    # only update customer.subscriber if both the customer and subscriber already exist
    if (
        subscriber_key not in ("", None)
        and metadata.get(subscriber_key, "")
        and customer_id
    ):
        try:
            subscriber = djstripe_settings.get_subscriber_model().objects.get(
                id=metadata.get(subscriber_key, "")
            )
            customer = models.Customer.objects.get(id=customer_id)
            customer.subscriber = subscriber
            customer.metadata = metadata
            customer.save()

        except ObjectDoesNotExist:
            pass


@webhooks.handler("customer")
def customer_webhook_handler(event):
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


@webhooks.handler("customer.discount")
def customer_discount_webhook_handler(event):
    """Handle updates to customer discount objects.

    Docs: https://stripe.com/docs/api#discounts

    Because there is no concept of a "Discount" model in dj-stripe (due to the
    lack of a stripe id on them), this is a little different to the other
    handlers.
    """

    crud_type = CrudType.determine(event=event)
    discount_data = event.data.get("object", {})
    coupon_data = discount_data.get("coupon", {})
    customer = event.customer

    if crud_type is CrudType.DELETED:
        coupon = None
        coupon_start = None
        coupon_end = None
    else:
        coupon, _ = _handle_crud_like_event(
            target_cls=models.Coupon,
            event=event,
            data=coupon_data,
            id=coupon_data.get("id"),
        )
        coupon_start = discount_data.get("start")
        coupon_end = discount_data.get("end")

    customer.coupon = coupon
    customer.coupon_start = convert_tstamp(coupon_start)
    customer.coupon_end = convert_tstamp(coupon_end)
    customer.save()


@webhooks.handler("customer.source")
def customer_source_webhook_handler(event):
    """Handle updates to customer payment-source objects.

    Docs: https://stripe.com/docs/api/sources
    """
    customer_data = event.data.get("object", {})
    source_type = customer_data.get("object", {})

    # TODO: handle other types of sources
    #  (https://stripe.com/docs/api/sources)
    if source_type == SourceType.card:
        if event.verb.endswith("deleted") and customer_data:
            # On customer.source.deleted, we do not delete the object,
            # we merely unlink it.
            # customer = Customer.objects.get(id=customer_data["id"])
            # NOTE: for now, customer.sources still points to Card
            # Also, https://github.com/dj-stripe/dj-stripe/issues/576
            models.Card.objects.filter(id=customer_data.get("id", "")).delete()
            models.DjstripePaymentMethod.objects.filter(
                id=customer_data.get("id", "")
            ).delete()
        else:
            _handle_crud_like_event(target_cls=models.Card, event=event)


@webhooks.handler("customer.subscription")
def customer_subscription_webhook_handler(event):
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


@webhooks.handler("customer.tax_id")
def customer_tax_id_webhook_handler(event):
    """
    Handle updates to customer tax ID objects.
    """
    _handle_crud_like_event(
        target_cls=models.TaxId, event=event, crud_type=CrudType.determine(event=event)
    )


@webhooks.handler("payment_method")
def payment_method_handler(event):
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


@webhooks.handler("account.external_account")
def account_application_webhook_handler(event):
    """
    Handles updates to Connected Accounts External Accounts
    """
    source_type = event.data.get("object", {}).get("object")
    if source_type == PayoutType.card:
        _handle_crud_like_event(target_cls=models.Card, event=event)

    if source_type == PayoutType.bank_account:
        _handle_crud_like_event(target_cls=models.BankAccount, event=event)


@webhooks.handler("account.updated")
def account_updated_webhook_handler(event):
    """
    Handles updates to Connected Accounts
        - account: https://stripe.com/docs/api/accounts
    """
    _handle_crud_like_event(
        target_cls=models.Account,
        event=event,
        crud_type=CrudType.UPDATED,
    )


@webhooks.handler("charge")
def charge_webhook_handler(event):
    """Handle updates to Charge objects
    - charge: https://stripe.com/docs/api/charges
    """
    # will recieve all events of the type charge.X.Y so
    # need to ensure the data object is related to Charge Object
    target_object_type = event.data.get("object", {}).get("object", {})

    if target_object_type == "charge":
        _handle_crud_like_event(target_cls=models.Charge, event=event)


@webhooks.handler("charge.dispute")
def dispute_webhook_handler(event):
    """Handle updates to Dispute objects
    - dispute: https://stripe.com/docs/api/disputes
    """
    # will recieve all events of the type charge.dispute.Y so
    # need to ensure the data object is related to Dispute Object
    target_object_type = event.data.get("object", {}).get("object", {})

    if target_object_type == "dispute":
        _handle_crud_like_event(target_cls=models.Dispute, event=event)


@webhooks.handler(
    "checkout",
    "coupon",
    "file",
    "invoice",
    "invoiceitem",
    "payment_intent",
    "plan",
    "price",
    "product",
    "setup_intent",
    "subscription_schedule",
    "source",
    "tax_rate",
    "transfer",
)
def other_object_webhook_handler(event):
    """
    Handle updates to checkout, coupon, file, invoice, invoiceitem, payment_intent,
    plan, product, setup_intent, subscription_schedule, source, tax_rate
    and transfer objects.

    Docs for:
    - checkout: https://stripe.com/docs/api/checkout/sessions
    - coupon: https://stripe.com/docs/api/coupons
    - file: https://stripe.com/docs/api/files
    - invoice: https://stripe.com/docs/api/invoices
    - invoiceitem: https://stripe.com/docs/api/invoiceitems
    - payment_intent: https://stripe.com/docs/api/payment_intents
    - plan: https://stripe.com/docs/api/plans
    - price: https://stripe.com/docs/api/prices
    - product: https://stripe.com/docs/api/products
    - setup_intent: https://stripe.com/docs/api/setup_intents
    - subscription_schedule: https://stripe.com/docs/api/subscription_schedules
    - source: https://stripe.com/docs/api/sources
    - tax_rate: https://stripe.com/docs/api/tax_rates/
    - transfer: https://stripe.com/docs/api/transfers
    """

    target_cls = {
        "checkout": models.Session,
        "coupon": models.Coupon,
        "file": models.File,
        "invoice": models.Invoice,
        "invoiceitem": models.InvoiceItem,
        "payment_intent": models.PaymentIntent,
        "plan": models.Plan,
        "price": models.Price,
        "product": models.Product,
        "transfer": models.Transfer,
        "setup_intent": models.SetupIntent,
        "subscription_schedule": models.SubscriptionSchedule,
        "source": models.Source,
        "tax_rate": models.TaxRate,
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

        # in case nothing matches
        return


def _handle_crud_like_event(
    target_cls,
    event,
    data=None,
    verb=None,
    id=None,
    customer=None,
    crud_type=None,
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
    :type event: models.Event
    :param data: The event object data (defaults to ``event.data``).
    :param verb: The event verb (defaults to ``event.verb``).
    :type verb: str
    :param id: The object Stripe ID (defaults to ``object.id``).
    :type id: str
    :param customer: The customer object (defaults to ``event.customer``).
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
        logger.debug(
            "Ignoring %r Stripe event without object ID: %r", event.type, event
        )
        return

    verb = verb or event.verb
    customer = customer or event.customer

    crud_type = crud_type or CrudType.determine(event=event, verb=verb)

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
            kwargs["customer"] = customer

        # For account.external_account.* events
        if event.parts[:2] == ["account", "external_account"] and stripe_account:
            kwargs["account"] = models.Account._get_or_retrieve(id=stripe_account)

        data = target_cls(**kwargs).api_retrieve(stripe_account=stripe_account)
        # create or update the object from the retrieved Stripe Data
        obj = target_cls.sync_from_stripe_data(data)

    return obj, crud_type
