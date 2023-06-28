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

## Legacy setup

Before dj-stripe 2.7.0, dj-stripe included a global webhook endpoint URL, which uses the
setting [`DJSTRIPE_WEBHOOK_SECRET`][djstripe.settings.DjstripeSettings.WEBHOOK_SECRET]
to validate incoming webhooks.

This is not recommended as it makes the URL guessable, and may be removed in the future.

## Extra configuration

dj-stripe provides the following settings to tune how your webhooks work:

-   [`DJSTRIPE_WEBHOOK_VALIDATION`][djstripe.settings.DjstripeSettings.WEBHOOK_VALIDATION]
-   [`DJSTRIPE_WEBHOOK_EVENT_CALLBACK`][djstripe.settings.DjstripeSettings.WEBHOOK_EVENT_CALLBACK]

## Advanced usage

dj-stripe comes with native support for webhooks as event listeners.

Events allow you to do things like sending an email to a customer when
his payment has
[failed](https://stripe.com/docs/receipts#failed-payment-alerts)
or trial period is ending.

This is how you use them:

```python
    from djstripe import webhooks

    @webhooks.handler("customer.subscription.trial_will_end")
    def my_handler(event, **kwargs):
        print("We should probably notify the user at this point")
```

You can handle all events related to customers like this:

```py
    from djstripe import webhooks

    @webhooks.handler("customer")
    def my_handler(event, **kwargs):
        print("We should probably notify the user at this point")
```

You can also handle different events in the same handler:

```py
from djstripe import webhooks

@webhooks.handler("price", "product")
def my_handler(event, **kwargs):
    print("Triggered webhook " + event.type)
```

!!! warning

    In order to get registrations picked up, you need to put them in a
    module that is imported like models.py or make sure you import it manually.

Webhook event creation and processing is now wrapped in a
`transaction.atomic()` block to better handle webhook errors. This will
prevent any additional database modifications you may perform in your
custom handler from being committed should something in the webhook
processing chain fail. You can also take advantage of Django's
`transaction.on_commit()` function to only perform an action if the
transaction successfully commits (meaning the Event processing worked):

```py
from django.db import transaction
from djstripe import webhooks

def do_something():
    pass  # send a mail, invalidate a cache, fire off a Celery task, etc.

@webhooks.handler("price", "product")
def my_handler(event, **kwargs):
    transaction.on_commit(do_something)
```

## Official documentation

Stripe docs for types of Events:
<https://stripe.com/docs/api/events/types>

Stripe docs for Webhooks: <https://stripe.com/docs/webhooks>

Django docs for transactions:
<https://docs.djangoproject.com/en/dev/topics/db/transactions/#performing-actions-after-commit>
