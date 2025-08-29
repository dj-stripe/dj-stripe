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

However in some cases `subscribe()` might not support all the arguments you need for your implementation.
When this happens you can just call the official `stripe.Customer.subscribe()`.
