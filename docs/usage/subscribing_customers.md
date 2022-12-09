# Subscribing a customer to one or more prices (or plans)

## Recommended Approach

```python
# Recommended Approach to use items dict with Prices
## This will subscribe <customer> to both <price_1> and <price_2>
price_1 = Price.objects.get(nickname="one_price")
price_2 = Price.objects.get(nickname="two_price")
customer = Customer.objects.first()
customer.subscribe(items=[{"price": price_1}, {"price": price_2}])

## This will subscribe <customer> to <price_1>
price_1 = Price.objects.get(nickname="one_price")
customer = Customer.objects.first()
customer.subscribe(items=[{"price": price_1}])

```

## Alternate Approach 1 (with legacy Plans)

```python
## (Alternate Approach) This will subscribe <customer> to <price_1>
price_1 = Price.objects.get(nickname="one_price")
customer = Customer.objects.first()
customer.subscribe(price=price_1)

# If you still use legacy Plans...
## This will subscribe <customer> to both <plan_1> and <plan_2>
plan_1 = Plan.objects.get(nickname="one_plan")
plan_2 = Plan.objects.get(nickname="two_plan")
customer = Customer.objects.first()
customer.subscribe(items=[{"plan": plan_1}, {"plan": plan_2}])

## This will subscribe <customer> to <plan_1>
plan_1 = Plan.objects.get(nickname="one_plan")
customer = Customer.objects.first()
customer.subscribe(items=[{"plan": plan_1}])
```

## Alternate Approach 2

```python

## (Alternate Approach) This will subscribe <customer> to <plan_1>
plan_1 = Plan.objects.get(nickname="one_plan")
customer = Customer.objects.first()
customer.subscribe(plan=plan_1)
```

However in some cases `subscribe()` might not
support all the arguments you need for your implementation. When this
happens you can just call the official `stripe.Customer.subscribe()`.

!!! tip
    Check out the following examples:

    -   [`form_valid view example`][tests.apps.example.views.PurchaseSubscriptionView.form_valid]
    -   [`djstripe.models.Customer.add_payment_method`][djstripe.models.core.Customer.add_payment_method]


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

    in the above example.
