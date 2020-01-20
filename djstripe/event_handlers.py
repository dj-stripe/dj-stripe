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

from . import models, webhooks
from .enums import SourceType
from .utils import convert_tstamp

logger = logging.getLogger(__name__)


@webhooks.handler("customer")
def customer_webhook_handler(event):
    """Handle updates to customer objects.

    First determines the crud_type and then handles the event if a customer
    exists locally.
    As customers are tied to local users, djstripe will not create customers that
    do not already exist locally.

    Docs and an example customer webhook response:
    https://stripe.com/docs/api#customer_object
    """
    if event.customer:
        # As customers are tied to local users, djstripe will not create
        # customers that do not already exist locally.
        _handle_crud_like_event(
            target_cls=models.Customer, event=event, crud_exact=True, crud_valid=True
        )


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

    if crud_type.created or crud_type.updated:
        coupon, _ = _handle_crud_like_event(
            target_cls=models.Coupon,
            event=event,
            data=coupon_data,
            id=coupon_data.get("id"),
        )
        coupon_start = discount_data.get("start")
        coupon_end = discount_data.get("end")
    else:
        coupon = None
        coupon_start = None
        coupon_end = None

    customer.coupon = coupon
    customer.coupon_start = convert_tstamp(coupon_start)
    customer.coupon_end = convert_tstamp(coupon_end)
    customer.save()


@webhooks.handler("customer.source")
def customer_source_webhook_handler(event):
    """Handle updates to customer payment-source objects.

    Docs: https://stripe.com/docs/api#customer_object-sources.
    """
    customer_data = event.data.get("object", {})
    source_type = customer_data.get("object", {})

    # TODO: handle other types of sources
    #  (https://stripe.com/docs/api#customer_object-sources)
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
    if crud_type.deleted:
        crud_type = CrudType(updated=True)
    _handle_crud_like_event(
        target_cls=models.Subscription, event=event, crud_type=crud_type
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
            crud_type=CrudType(deleted=True),
        )
    else:
        _handle_crud_like_event(target_cls=models.PaymentMethod, event=event)


@webhooks.handler(
    "charge",
    "coupon",
    "invoice",
    "invoiceitem",
    "payment_intent",
    "plan",
    "product",
    "setup_intent",
    "source",
    "tax_rate",
    "transfer",
)
def other_object_webhook_handler(event):
    """
    Handle updates to charge, coupon, invoice, invoiceitem, payment_intent,
    plan, product, setup_intent, source, tax_rate and transfer objects.

    Docs for:
    - charge: https://stripe.com/docs/api/charges
    - coupon: https://stripe.com/docs/api/coupons
    - invoice: https://stripe.com/docs/api/invoices
    - invoiceitem: https://stripe.com/docs/api/invoiceitems
    - payment_intent: https://stripe.com/docs/api/payment_intents
    - plan: https://stripe.com/docs/api/plans
    - product: https://stripe.com/docs/api/products
    - setup_intent: https://stripe.com/docs/api/setup_intents
    - source: https://stripe.com/docs/api/sources
    - tax_rate: https://stripe.com/docs/api/tax_rates/
    - transfer: https://stripe.com/docs/api/transfers
    """

    if event.parts[:2] == ["charge", "dispute"]:
        # Do not attempt to handle charge.dispute.* events.
        # We do not have a Dispute model yet.
        target_cls = models.Dispute
    else:
        target_cls = {
            "charge": models.Charge,
            "coupon": models.Coupon,
            "invoice": models.Invoice,
            "invoiceitem": models.InvoiceItem,
            "payment_intent": models.PaymentIntent,
            "plan": models.Plan,
            "product": models.Product,
            "transfer": models.Transfer,
            "setup_intent": models.SetupIntent,
            "source": models.Source,
            "tax_rate": models.TaxRate,
        }.get(event.category)

    _handle_crud_like_event(target_cls=target_cls, event=event)


#
# Helpers
#


class CrudType(object):
    """Helper object to determine CRUD-like event state."""

    created = False
    updated = False
    deleted = False

    def __init__(self, **kwargs):
        """Set attributes."""
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def valid(self):
        """Return True if this is a CRUD-like event."""
        return self.created or self.updated or self.deleted

    @classmethod
    def determine(cls, event, verb=None, exact=False):
        """
        Determine if the event verb is a crud_type (without the 'R') event.

        :param event:
        :type event: models.Event
        :param verb: The event verb to examine.
        :type verb: str
        :param exact: If True, match crud_type to event verb string exactly.
        :type exact: bool
        :returns: The CrudType state object.
        :rtype: CrudType
        """
        verb = verb or event.verb

        def check(crud_type_event):
            if exact:
                return verb == crud_type_event
            else:
                return verb.endswith(crud_type_event)

        created = updated = deleted = False

        if check("updated"):
            updated = True
        elif check("created"):
            created = True
        elif check("deleted"):
            deleted = True

        return cls(created=created, updated=updated, deleted=deleted)


def _handle_crud_like_event(
    target_cls,
    event,
    data=None,
    verb=None,
    id=None,
    customer=None,
    crud_type=None,
    crud_exact=False,
    crud_valid=False,
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
    :param crud_exact: If True, match verb against CRUD type exactly.
    :param crud_valid: If True, CRUD type must match valid type.
    :returns: The object (if any) and the event CrudType.
    :rtype: Tuple[models.StripeModel, CrudType]
    """
    data = data or event.data
    id = id or data.get("object", {}).get("id", None)

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
    crud_type = crud_type or CrudType.determine(
        event=event, verb=verb, exact=crud_exact
    )
    obj = None

    if crud_valid and not crud_type.valid:
        logger.debug(
            "Ignoring %r Stripe event without valid CRUD type: %r", event.type, event
        )
        return

    if crud_type.deleted:
        qs = target_cls.objects.filter(id=id)
        if target_cls is models.Customer and qs.exists():
            qs.get().purge()
        else:
            obj = target_cls.objects.filter(id=id).delete()
    else:
        # Any other event type (creates, updates, etc.) - This can apply to
        # verbs that aren't strictly CRUD but Stripe do intend an update.  Such
        # as invoice.payment_failed.
        kwargs = {"id": id}
        if hasattr(target_cls, "customer"):
            kwargs["customer"] = customer
        data = target_cls(**kwargs).api_retrieve()
        obj = target_cls.sync_from_stripe_data(data)

    return obj, crud_type
