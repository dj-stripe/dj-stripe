=========
Settings
=========

DJSTRIPE_DEFAULT_PLAN (=None)
=============================

Payment plans default. 

Possibly deprecated in favor of model based plans.

DJSTRIPE_INVOICE_FROM_EMAIL (="billing@example.com")
====================================================

Invoice emails come from this address.

DJSTRIPE_PLANS (={})
====================

Payment plans. 

Possibly deprecated in favor of model based plans.

Example:

.. code-block:: python

    DJSTRIPE_PLANS = {
        "monthly": {
            "stripe_plan_id": "pro-monthly",
            "name": "Web App Pro ($24.99/month)",
            "description": "The monthly subscription plan to WebApp",
            "price": 2499,  # $24.99
            "currency": "usd",
            "interval": "month",
            "image": "img/pro-monthly.png"
        },
        "yearly": {
            "stripe_plan_id": "pro-yearly",
            "name": "Web App Pro ($199/year)",
            "description": "The annual subscription plan to WebApp",
            "price": 19900,  # $199.00
            "currency": "usd",
            "interval": "year",
            "image": "img/pro-yearly.png"
        }
    }

.. note:: Stripe Plan creation

    Not all properties listed in the plans above are used by Stripe - i.e 'description' and 'image',
    which are used to display the plans description and related image within specific templates.

    Although any arbitrary property you require can be added to each plan listed in DJ_STRIPE_PLANS,
    only specific properties are used by Stripe. The full list of required and optional arguments can
    be found here_.

.. _here: https://stripe.com/docs/api/python#create_plan

DJSTRIPE_PLAN_HIERARCHY (={})
=============================

Payment plans levels. 

Allows you to set levels of access to the plans.

Example:

.. code-block:: python

    DJSTRIPE_PLANS = {
        "bronze-monthly": {
            ...
        },
        "bronze-yearly": {
            ...
        },
        "silver-monthly": {
            ...
        },
        "silver-yearly": {
            ...
        },
        "gold-monthly": {
            ...
        },
        "gold-yearly": {
            ...
        }
    }

    DJSTRIPE_PLAN_HIERARCHY = {
        "bronze": {
            "level": 1,
            "plans": [
                "bronze-monthly",
                "bronze-yearly",
            ]
        },
        "silver": {
            "level": 2,
            "plans": [
                "silver-monthly",
                "silver-yearly",
            ]
        },
        "gold": {
            "level": 3,
            "plans": [
                "gold-monthly",
                "gold-yearly",
            ]
        },
    }

Use:

.. code-block:: python

    {% <plan_name>|djstripe_plan_level %}

Example:

.. code-block:: python

    {% elif customer.subscription.plan == plan.plan %}
        <h4>Your Current Plan</h4>
    {% elif customer.subscription|djstripe_plan_level < plan.plan|djstripe_plan_level %}
        <h4>Upgrade</h4>
    {% elif customer.subscription|djstripe_plan_level > plan.plan|djstripe_plan_level %}
        <h4>Downgrade</h4>
    {% endif %}
    
DJSTRIPE_PRORATION_POLICY (=False)
==================================

By default, plans are not prorated in dj-stripe. Concretely, this is how this translates: 

1) If a customer cancels their plan during a trial, the cancellation is effective right away.
2) If a customer cancels their plan outside of a trial, their subscription remains active until the subscription's period end, and they do not receive a refund.
3) If a customer switches from one plan to another, the new plan becomes effective right away, and the customer is billed for the new plan's amount.

Assigning ``True`` to ``DJSTRIPE_PRORATION_POLICY`` reverses the functioning of item 2 (plan cancellation) by making a cancellation effective right away and refunding the unused balance to the customer, and affects the functioning of item 3 (plan change) by prorating the previous customer's plan towards their new plan's amount.

DJSTRIPE_PRORATION_POLICY_FOR_UPGRADES (=False)
===============================================

By default, the plan change policy described in item 3 above holds also for plan upgrades.

Assigning ``True`` to ``DJSTRIPE_PRORATION_POLICY_FOR_UPGRADES`` allows dj-stripe to prorate plans in the specific case of an upgrade. Therefore, if a customer upgrades their plan, their new plan is effective right away, and they get billed for the new plan's amount minus the unused balance from their previous plan.

DJSTRIPE_SEND_INVOICE_RECEIPT_EMAILS (=True)
============================================

By default dj-stripe sends emails for each receipt. You can turn this off by
setting this value to ``False``.


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

DJSTRIPE_TRIAL_PERIOD_FOR_SUBSCRIBER_CALLBACK (=None)
=====================================================

Used by ``djstripe.models.Customer`` only when creating stripe customers when you have a default plan set via ``DJSTRIPE_DEFAULT_PLAN``.

This is called to dynamically add a trial period to a subscriber's plan. It must be a callable or importable string to a callable that takes a subscriber object and returns the number of days the trial period should last.

Examples:

.. code-block:: python

    def static_trial_period(subscriber):
        """ Adds a static trial period of 7 days to each subscriber's account."""
        return 7


    def dynamic_trial_period(subscriber):
        """
        Adds a static trial period of 7 days to each subscriber's plan,
        unless they've accepted our month-long promotion.
        """
        
        if subscriber.coupons.get(slug="monthlongtrial"):
            return 30
        else:
            return 7

.. note:: This setting was named ``DJSTRIPE_TRIAL_PERIOD_FOR_USER_CALLBACK`` prior to version 0.4


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
        log.debug("Processing Stripe event: %s", str(event))
        try:
            event.process(raise_exception=True):
        except StripeError as exc:
            log.error("Failed to process Stripe event: %s", str(event))
            raise self.retry(exc=exc, countdown=60)  # retry after 60 seconds

`settings.py`

.. code-block:: python

    DJSTRIPE_WEBHOOK_EVENT_CALLBACK = 'callbacks.webhook_event_callback'

DJSTRIPE_CURRENCIES (=(('usd', 'U.S. Dollars',), ('gbp', 'Pounds (GBP)',), ('eur', 'Euros',)))
==============================================================================================

A Field.choices list of allowed currencies for Plan models.
