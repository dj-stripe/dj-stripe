# Subscribing a customer to a price (or plan)

For your convenience, dj-stripe provides a
`djstripe.models.Customer.subscribe` method that will try to charge the
customer immediately unless you specify `charge_immediately=False`

```py
price = Price.objects.get(nickname="one_price")
customer = Customer.objects.first()
customer.subscribe(price=price)

# If you still use legacy Plans...
plan = Plan.objects.get(nickname="one_plan")
customer = Customer.objects.first()
customer.subscribe(plan=plan)
```

However in some cases `djstripe.models.Customer.subscribe` might not
support all the arguments you need for your implementation. When this
happens you can just call the official `stripe.Customer.subscribe()`.

See this example from
`tests.apps.example.views.PurchaseSubscriptionView.form_valid`.

Note that PaymentMethods can be used instead of Cards/Source by
substituting

```py
# Add the payment method customer's default
customer.add_payment_method(payment_method)
```

instead of

```py
# Add the source as the customer's default card
customer.add_card(stripe_source)
```

in the above example. See `djstripe.models.Customer.add_payment_method`.
