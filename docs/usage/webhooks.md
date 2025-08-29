# Using Stripe Webhooks

## Setting up a new webhook endpoint in dj-stripe

As of dj-stripe 2.7.0, dj-stripe can create its own webhook endpoints on Stripe from the
Django administration.

Create a new webhook endpoint from the Django administration by going to dj-stripe
-> Webhook endpoints -> Add webhook endpoint (or `/admin/djstripe/webhookendpoint/add/`).

From there, you can choose an account to create the endpoint for.
If no account is chosen, the default Stripe API key will be used to create the endpoint.
You can also choose to create the endpoint in test mode or live mode.

You may want to change the base URL of the endpoint. This field will be prefilled with
the current site. If you're running on the local development server, you may see
`http://localhost:8000` or similar in there. Stripe won't let you save webhook endpoints
with such a value, so you will want to change it to a real website URL.

When saved from the admin, the endpoint will be created in Stripe with a dj-stripe
specific UUID which will be part of the URL, making it impossible to guess externally
by brute-force.

## Extra configuration

dj-stripe provides the following settings to tune how your webhooks work:

- [`DJSTRIPE_WEBHOOK_VALIDATION`][djstripe.settings.DjstripeSettings.WEBHOOK_VALIDATION]
- [`DJSTRIPE_WEBHOOK_EVENT_CALLBACK`][djstripe.settings.DjstripeSettings.WEBHOOK_EVENT_CALLBACK]

## Handling Stripe Webhooks Using Django Signals in dj-stripe

dj-stripe integrates with Django's signals framework to provide a robust mechanism for handling Stripe webhook events. This approach allows developers to react to Stripe events by executing custom logic linked to signal receivers. This document guides you through setting up and using Django signals with dj-stripe to handle various Stripe webhook events efficiently.

### Configuring Webhook Endpoints

Before you can handle webhook events, ensure you've configured your webhook endpoints correctly in Stripe and dj-stripe. This can typically be done from the Django admin panel under dj-stripe -> Webhook endpoints.

### Event Processing Flow

1. **Receiving Events**: When Stripe sends a webhook event, dj-stripe receives the data and creates an `Event` object in your Django database.
2. **Emitting Signals**: After storing the event, dj-stripe emits a Django signal corresponding to the event type (e.g., `charge.succeeded`, `payment_method.attached`).
3. **Database Operations by dj-stripe**: dj-stripe also listens to these signals to perform CRUD operations on corresponding Django models, such as `Charge` or `PaymentMethod`. This ensures that your database stays in sync with the Stripe data.
4. **Handling Events**: You can handle these signals with custom functions linked via the `djstripe_receiver` decorator.

### Implementing Custom Event Handlers

To create custom handlers for Stripe webhook events, follow these steps:

#### 1. Set Up Signal Handlers

First, import the necessary modules and decorators from dj-stripe and define functions to handle the events of interest.

```python
from djstripe.event_handlers import djstripe_receiver
from djstripe.models import Event, Charge, PaymentMethod

@djstripe_receiver("charge.succeeded")
def handle_charge_succeeded(sender, **kwargs):
    event: Event = kwargs.get("event")
    charge_id = event.data["object"]["id"]
    charge = Charge.objects.get(id=charge_id)
    print("Charge succeeded!")
    print(f"Sender: {sender}")
    print(f"Event: {event}")
    print(f"Charge: {charge}")

@djstripe_receiver("payment_method.attached")
def handle_payment_method_attached(sender, **kwargs):
    event: Event = kwargs.get("event")
    payment_method_id = event.data["object"]["id"]
    payment_method = PaymentMethod.objects.get(id=payment_method_id)
    print("Payment Method Attached!")
    print(f"Sender: {sender}")
    print(f"Event: {event}")
    print(f"Payment Method: {payment_method}")
```

#### 2. Ensure Proper Loading of Handlers

Ensure that your custom signal handlers are loaded at the appropriate time by including their module in your application's startup sequence. Typically, this can be handled in the `apps.py` of your Django application by overriding the `ready()` method.

```python
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = 'my_app'

    def ready(self):
        import my_app.signals  # ensure your signals are imported
```

## Official documentation

Stripe docs for types of Events:
https://stripe.com/docs/api/events/types

Stripe docs for Webhooks: https://stripe.com/docs/webhooks

Django docs for transactions:
https://docs.djangoproject.com/en/dev/topics/db/transactions/#performing-actions-after-commit
