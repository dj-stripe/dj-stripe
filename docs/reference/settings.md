# Settings

## STRIPE_API_VERSION (='2020-08-27')

The API version used to communicate with the Stripe API is configurable, and defaults to
the latest version that has been tested as working. Using a value other than the default
is allowed, as a string in the format of YYYY-MM-DD.

For example, you can specify `"2020-03-02"` to use that API version:

```py
STRIPE_API_VERSION = "2020-03-02"
```

However you do so at your own risk, as using a value other than the default might result
in incompatibilities between Stripe and this library, especially if Stripe has labelled
the differences between API versions as "Major". Even small differences such as a new
enumeration value might cause issues.

For this reason it is best to assume that only the default version is supported.

For more information on API versioning, see the [stripe
documentation](https://stripe.com/docs/upgrades).

See also [API Versions](../api_versions.md#a_note_on_stripe_api_versions).

## DJSTRIPE_IDEMPOTENCY_KEY_CALLBACK (=djstripe.settings.djstripe_settings.\_get_idempotency_key)

A function which will return an idempotency key for a particular object_type and action
pair. By default, this is set to a function which will create a
`djstripe.IdempotencyKey` object and return its `uuid`. You may want to customize this
if you want to give your idempotency keys a different lifecycle than they normally would
get.

The function takes the following signature:

```py
def get_idempotency_key(object_type: str, action: str, livemode: bool):
    return "<idempotency key>"
```

The function MUST return a string suitably random for the object_type/action pair, and
usable in the Stripe `Idempotency-Key` HTTP header. For more information, see the
[stripe documentation](https://stripe.com/docs/upgrades).

## DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY (="djstripe_subscriber")

Every Customer object created in Stripe is tagged with
[metadata](https://stripe.com/docs/api#metadata) This setting controls what the name of
the key in Stripe should be. The key name must be a string no more than 40 characters
long.

You may set this to `None` or `""` to disable that behaviour altogether. This is
probably not something you want to do, though.

## DJSTRIPE_SUBSCRIBER_MODEL (=settings.AUTH_USER_MODEL)

If the AUTH_USER_MODEL doesn't represent the object your application's subscription
holder, you may define a subscriber model to use here. It should be a string in the form
of 'app.model'.

!!! note

    DJSTRIPE_SUBSCRIBER_MODEL must have an `email` field. If your
    existing model has no email field, add an email property that
    defines an email address to use.

Example Model:

```py
class Organization(models.Model):
    name = CharField(max_length=200, unique=True)
    admin = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE)

    @property
    def email(self):
        return self.admin.email
```

## DJSTRIPE_SUBSCRIBER_MODEL_MIGRATION_DEPENDENCY (="\_\_first\_\_")

If the model referenced in DJSTRIPE_SUBSCRIBER_MODEL is not created in the `__first__`
migration of an app you can specify the migration name to depend on here. For example:
"0003_here_the_subscriber_model_was_added"



## DJSTRIPE_WEBHOOK_EVENT_CALLBACK (=None)

Webhook event callbacks allow an application to take control of what happens when an
event from Stripe is received. It must be a callable or importable string to a callable
that takes an event object.

One suggestion is to put the event onto a task queue (such as celery) for asynchronous
processing.

Examples:

```py
# callbacks.py
def webhook_event_callback(event, api_key):
    """ Dispatches the event to celery for processing. """
    from . import tasks
    # Ansychronous hand-off to celery so that we can continue immediately
    tasks.process_webhook_event.s(event.pk, api_key).apply_async()
```

```py
# tasks.py
from djstripe.models import WebhookEventTrigger
from stripe.error import StripeError

@shared_task(bind=True)
def process_webhook_event(self, pk, api_key):
    """ Processes events from Stripe asynchronously. """
    logger.info(f"Processing Stripe event: {pk}")
    try:
        # get the event
        obj = WebhookEventTrigger.objects.get(pk=pk)
        # process the event.
        # internally, this creates a Stripe WebhookEvent Object and invokes the respective Webhooks
        try:
            event = obj.process(save=False, api_key=api_key)
            # only save the event if webhook process was successfuly, otherwise it won't retry
            event.save()
        except StripeError as exc:
            # Mark the event as not processed
            obj.processed = False
            obj.save()
            logger.error(f"Failed to process Stripe event: {pk}. Retrying in 60 seconds.")
            raise self.retry(exc=exc, countdown=60)  # retry after 60 seconds
    except WebhookEventTrigger.DoesNotExist as exc:
        # This can happen in case the celery task got executed before the actual model got saved to the DB
        raise self.retry(exc=exc, countdown=10)  # retry after 10 seconds

    return event.type or "Stripe Event Processed"
```

```py
# settings.py
DJSTRIPE_WEBHOOK_EVENT_CALLBACK = 'callbacks.webhook_event_callback'
```

## STRIPE_API_HOST (= unset)

If set, this sets the base API host for Stripe. You may want to set this to, for
example, `"http://localhost:12111"` if you are running
[stripe-mock](https://github.com/stripe/stripe-mock).

If this is set in production (DEBUG=False), a warning will be raised on `manage.py check`.

## Source Code

::: djstripe.settings
selection:
filters: - "!^_[^_]"
