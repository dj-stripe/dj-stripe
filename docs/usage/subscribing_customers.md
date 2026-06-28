# Subscribing a customer to one or more prices (or plans)

## Recommended Approach

```python
# Recommended Approach to use items dict with Prices
## This will subscribe customer to both price_1 and price_2
price_1 = Price.objects.get(nickname="one_price")
price_2 = Price.objects.get(nickname="two_price")
customer = Customer.objects.first()
customer.subscribe(items=[{"price": price_1}, {"price": price_2}])

## This will subscribe customer to price_1
price_1 = Price.objects.get(nickname="one_price")
customer = Customer.objects.first()
customer.subscribe(items=[{"price": price_1}])
```

## Alternate Approach

```python
## (Alternate Approach) This will subscribe customer to price_1
price_1 = Price.objects.get(nickname="one_price")
customer = Customer.objects.first()
customer.subscribe(price=price_1)
```

In some cases [`Customer.subscribe()`][djstripe.models.core.Customer.subscribe] might
not expose every argument you need. When that happens, create the subscription
directly with the Stripe API and sync the result back into dj-stripe:

```python
import stripe
from djstripe.models import Subscription

stripe_subscription = stripe.Subscription.create(
    customer=customer.id,
    items=[{"price": price_1.id}],
    api_key="sk_test_...",
)
subscription = Subscription.sync_from_stripe_data(stripe_subscription)
```

See [Manually syncing data with Stripe](manually_syncing_with_stripe.md) for more
on `sync_from_stripe_data`.
