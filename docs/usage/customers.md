# Working with customers

The [`Customer`][djstripe.models.core.Customer] model is the hub of most dj-stripe
integrations. It links one of your **subscribers** (by default your
`AUTH_USER_MODEL`, configurable via
[`DJSTRIPE_SUBSCRIBER_MODEL`](../settings.md#djstripe_subscriber_model)) to a Stripe
customer, and exposes helper methods for the common billing workflows.

## Getting a customer

Use [`Customer.get_or_create`][djstripe.models.core.Customer.get_or_create] to fetch
or create the Stripe customer for a subscriber. This is the usual entry point:

```python
from djstripe.models import Customer

customer, created = Customer.get_or_create(subscriber=request.user)
```

The first call creates the customer in Stripe and stores it locally; subsequent
calls return the existing record.

## Helper methods

`Customer` wraps the most common operations so you rarely need to call the Stripe
API directly:

| Method | Purpose |
| --- | --- |
| [`subscribe()`][djstripe.models.core.Customer.subscribe] | Subscribe the customer to one or more prices. See [Subscribing customers](subscribing_customers.md). |
| [`charge()`][djstripe.models.core.Customer.charge] | Create a one-off charge. See [Creating individual charges](creating_individual_charges.md). |
| [`add_payment_method()`][djstripe.models.core.Customer.add_payment_method] | Attach a payment method. See [Adding a payment method](add_payment_method_to_customer.md). |
| [`add_invoice_item()`][djstripe.models.core.Customer.add_invoice_item] | Add a one-off line item to the customer's next invoice. |
| [`add_coupon()`][djstripe.models.core.Customer.add_coupon] | Apply a coupon to the customer. |
| [`is_subscribed_to()`][djstripe.models.core.Customer.is_subscribed_to] | Check whether the customer has an active subscription to a given product. |
| [`has_any_active_subscription()`][djstripe.models.core.Customer.has_any_active_subscription] | Whether the customer has any active subscription. |
| [`send_invoice()`][djstripe.models.core.Customer.send_invoice] | Create and send an invoice. |
| [`upcoming_invoice()`][djstripe.models.core.Customer.upcoming_invoice] | Preview the customer's next invoice. |
| [`purge()`][djstripe.models.core.Customer.purge] | Delete the customer in Stripe and detach it locally. |

## Accessing subscriptions

Because Stripe data is mirrored into Django models, you query a customer's related
objects through the ORM. `Customer` also provides convenience properties:

```python
# Convenience properties:
customer.subscription          # the customer's single active subscription, or None
customer.active_subscriptions  # queryset of active subscriptions
customer.valid_subscriptions   # active subscriptions that have not ended

# Or query the related models directly:
customer.subscriptions.all()
customer.invoices.all()
customer.charges.all()
```

See the [`Customer` API reference][djstripe.models.core.Customer] for the full list
of methods, properties and relations.
