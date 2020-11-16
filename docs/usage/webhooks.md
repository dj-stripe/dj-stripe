# Using Stripe Webhooks

## Available settings

dj-stripe provides the following settings to tune how your webhooks work:

-   [DJSTRIPE_WEBHOOK_URL](../reference/settings.md#djstripe_webhook_url-rwebhook)
-   [DJSTRIPE_WEBHOOK_SECRET](../reference/settings.md#djstripe_webhook_secret)
-   [DJSTRIPE_WEBHOOK_VALIDATION](../reference/settings.md#djstripe_webhook_validation-verify_signature)
-   [DJSTRIPE_WEBHOOK_TOLERANCE](../reference/settings.md#djstripe_webhook_tolerance-300)
-   [DJSTRIPE_WEBHOOK_EVENT_CALLBACK](../reference/settings.md#djstripe_webhook_event_callback-none)

## Using webhooks in dj-stripe

dj-stripe comes with native support for webhooks as event listeners.

Events allow you to do things like [sending an email to a customer when
his payment has
[failed](https://stripe.com/docs/recipes/sending-emails-for-failed-payments)
or trial period is ending.

This is how you use them:

```py
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
