# How to add payment method to a customer

You can use the [`add_payment_method`][djstripe.models.core.Customer.add_payment_method] method on a customer object to add a payment method token to a customer on Stripe, this will allow you to charge the customer later on that payment method since it will be added as the default payment method.

```python
from djstripe.models import Customer

customer = Customer.objects.first() # Get the first customer in the database as an example
customer.add_payment_method("pm_card_visa") # Add a payment method to the customer as the default payment method
```

If you want to add a payment method to a customer without making it the default payment method, you can use the [`add_payment_method`][djstripe.models.core.Customer.add_payment_method] and pass the parameter `set_default=False`:

```python
from djstripe.models import Customer

customer = Customer.objects.first() # Get the first customer in the database as an example
customer.add_payment_method("pm_card_visa", set_default=False) # Add a payment method to the customer without making it the default payment method
```

**IMPORTANT**: Please keep in mind that due to securities concerns, Stripe will not let you send credit card information through their API, so you will need to use a Stripe token to add a payment method to a customer. You can read more about Stripe tokens [here](https://stripe.com/docs/api/tokens).
