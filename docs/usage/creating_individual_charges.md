# Creating individual charges

On the subscriber's customer object, use the `charge` method to generate a
Stripe charge. In this example, we're using the user named `admin` as the
subscriber.

```py
from decimal import Decimal
from django.contrib.auth import get_user_model
from djstripe.models import Customer

user = get_user_model().objects.get(username="admin")
customer, created = Customer.get_or_create(subscriber=user)
customer.charge(Decimal(10.00), currency="usd")  # Create charge for 10.00 USD
```
