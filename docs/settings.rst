=========
Settings
=========

STRIPE_API_VERSION (='2017-02-14')
==================================

The API version used to communicate with the Stripe API is configurable, and
defaults to the latest version that has been tested as working. Using a value
other than the default is allowed, as a string in the format of YYYY-MM-DD.

For example, you can specify `'2017-01-27'` to use that API version:

.. code-block:: python

    STRIPE_API_VERSION = '2017-01-27'

However you do so at your own risk, as using a value other than the default
might result in incompatibilities between Stripe and this library, especially
if Stripe has labelled the differences between API versions as "Major". Even
small differences such as a new enumeration value might cause issues.

For this reason it is best to assume that only the default version is supported.

For more information on API versioning, see the `stripe documentation`_.

.. _stripe documentation: https://stripe.com/docs/upgrades


DJSTRIPE_IDEMPOTENCY_KEY_CALLBACK (=djstripe.settings._get_idempotency_key)
===========================================================================

A function which will return an idempotency key for a particular object_type
and action pair. By default, this is set to a function which will create a
``djstripe.IdempotencyKey`` object and return its ``uuid``.
You may want to customize this if you want to give your idempotency keys a
different lifecycle than they normally would get.

The function takes the following signature:

.. code-block:: python

    def get_idempotency_key(object_type: str, action: str, livemode: bool):
        return "<idempotency key>"

The function MUST return a string suitably random for the object_type/action
pair, and usable in the Stripe ``Idempotency-Key`` HTTP header.
For more information, see the `stripe documentation`_.

.. _stripe documentation: https://stripe.com/docs/api/curl#idempotent_requests

DJSTRIPE_PRORATION_POLICY (=False)
==================================

By default, plans are not prorated in dj-stripe. Concretely, this is how this translates:

1) If a customer cancels their plan during a trial, the cancellation is effective right away.
2) If a customer cancels their plan outside of a trial, their subscription remains active until the subscription's period end, and they do not receive a refund.
3) If a customer switches from one plan to another, the new plan becomes effective right away, and the customer is billed for the new plan's amount.

Assigning ``True`` to ``DJSTRIPE_PRORATION_POLICY`` reverses the functioning of item 2 (plan cancellation) by making a cancellation effective right away and refunding the unused balance to the customer, and affects the functioning of item 3 (plan change) by prorating the previous customer's plan towards their new plan's amount.

DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS (=())
===================================================

Used by ``djstripe.middleware.SubscriptionPaymentMiddleware``

Rules:

* "(app_name)" means everything from this app is exempt
* "[namespace]" means everything with this name is exempt
* "namespace:name" means this namespaced URL is exempt
* "name" means this URL is exempt
* The entire djstripe namespace is exempt
* If settings.DEBUG is True, then django-debug-toolbar is exempt

Example:

.. code-block:: python

    DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS = (
        "(allauth)",  # anything in the django-allauth URLConf
        "[blogs]",  # Anything in the blogs namespace
        "products:detail",  # A ProductDetail view you want shown to non-payers
        "home",  # Site homepage
    )

.. note:: Adding app_names to applications.

    To make the ``(allauth)`` work, you may need to define an app_name in the ``include()`` function in the URLConf. For example::

        # in urls.py
        url(r'^accounts/', include('allauth.urls',  app_name="allauth")),


DJSTRIPE_SUBSCRIBER_MODEL (=settings.AUTH_USER_MODEL)
=====================================================

If the AUTH_USER_MODEL doesn't represent the object your application's subscription holder, you may define a subscriber model to use here. It should be a string in the form of 'app.model'.

Rules:

* DJSTRIPE_SUBSCRIBER_MODEL must have an ``email`` field. If your existing model has no email field, add an email property that defines an email address to use.
* You must also implement ``DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK``.

Example Model:

.. code-block:: python

    class Organization(models.Model):
        name = CharField(max_length=200, unique=True)
        subdomain = CharField(max_length=63, unique=True, verbose_name="Organization Subdomain")
        owner = ForeignKey(settings.AUTH_USER_MODEL, related_name="organization_owner", verbose_name="Organization Owner")

        @property
        def email(self):
            return self.owner.email


DJSTRIPE_SUBSCRIBER_MODEL_MIGRATION_DEPENDENCY (="__first__")
=============================================================
If the model referenced in DJSTRIPE_SUBSCRIBER_MODEL is not created in the ``__first__`` migration of an app you can specify the migration name to depend on here. For example: "0003_here_the_subscriber_model_was_added"


DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK (=None)
==================================================

If you choose to use a custom subscriber model, you'll need a way to pull it from ``request``. That's where this callback comes in.
It must be a callable or importable string to a callable that takes a request object and returns an instance of DJSTRIPE_SUBSCRIBER_MODEL

Examples:

`middleware.py`

.. code-block:: python

    class DynamicOrganizationIDMiddleware(object):
        """ Adds the current organization's ID based on the subdomain."""

        def process_request(self, request):
            subdomain = parse_subdomain(request.get_host())

            try:
                organization = Organization.objects.get(subdomain=subdomain)
            except Organization.DoesNotExist:
                return TemplateResponse(request=request, template='404.html', status=404)
            else:
                organization_id = organization.id

            request.organization_id = organization_id

`settings.py`

.. code-block:: python

    def organization_request_callback(request):
        """ Gets an organization instance from the id passed through ``request``"""

        from <models_path> import Organization  # Import models here to avoid an ``AppRegistryNotReady`` exception
        return Organization.objects.get(id=request.organization_id)


.. note:: This callback only becomes active when ``DJSTRIPE_SUBSCRIBER_MODEL`` is set.


DJSTRIPE_USE_NATIVE_JSONFIELD (=False)
======================================

Setting this to ``True`` will make the various dj-stripe JSON fields use
``django.contrib.postgres.fields.JSONField`` instead of the ``jsonfield``
library (which internally uses ``text`` fields).

The native Django JSONField uses the postgres `jsonb`_ column type, which
efficiently stores JSON and can be queried far more conveniently. Django also
supports `querying JSONField`_ with the ORM.

.. note:: This is only supported on Postgres databases.

.. note:: **Migrating between native and non-native must be done manually.**

.. _jsonb: https://www.postgresql.org/docs/9.6/static/functions-json.html

.. _querying JSONField: https://docs.djangoproject.com/en/1.11/ref/contrib/postgres/fields/#querying-jsonfield


DJSTRIPE_WEBHOOK_URL (=r"^webhook/$")
=====================================

This is where you can set *Stripe.com* to send webhook response. You can set this to what you want to prevent unnecessary hijinks from unfriendly people.

As this is embedded in the URLConf, this must be a resolvable regular expression.

DJSTRIPE_WEBHOOK_EVENT_CALLBACK (=None)
=======================================

Webhook event callbacks allow an application to take control of what happens when an event from Stripe is received.
It must be a callable or importable string to a callable that takes an event object.

One suggestion is to put the event onto a task queue (such as celery) for asynchronous processing.

Examples:

`callbacks.py`

.. code-block:: python

    def webhook_event_callback(event):
        """ Dispatches the event to celery for processing. """
        from . import tasks
        # Ansychronous hand-off to celery so that we can continue immediately
        tasks.process_webhook_event.s(event).apply_async()

`tasks.py`

.. code-block:: python

    from stripe.error import StripeError

    @shared_task(bind=True)
    def process_webhook_event(self, event):
        """ Processes events from Stripe asynchronously. """
        logger.info("Processing Stripe event: %s", str(event))
        try:
            event.process(raise_exception=True)
        except StripeError as exc:
            logger.error("Failed to process Stripe event: %s", str(event))
            raise self.retry(exc=exc, countdown=60)  # retry after 60 seconds

`settings.py`

.. code-block:: python

    DJSTRIPE_WEBHOOK_EVENT_CALLBACK = 'callbacks.webhook_event_callback'
