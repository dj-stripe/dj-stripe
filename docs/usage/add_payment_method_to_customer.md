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

**IMPORTANT**: For security reasons, Stripe does not let you send raw credit card numbers through their API. You collect card details in the browser with [Stripe.js / Elements](../stripe_elements_js.md), which returns a payment method identifier (e.g. `pm_...`) that you then pass to `add_payment_method`. See [Stripe's payment methods documentation](https://stripe.com/docs/payments/payment-methods).
