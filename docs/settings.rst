Settings
=========

Available settings:

DJSTRIPE_DEFAULT_PLAN (=None)
-----------------------------

Payment plans default. 

Possibly deprecated in favor of model based plans.

DJSTRIPE_INVOICE_FROM_EMAIL (="billing@example.com")
----------------------------------------------------

Invoice emails come from this address.

DJSTRIPE_PLANS (={})
--------------------

Payment plans. 

Possibly deprecated in favor of model based plans.


DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS (=())
---------------------------------------------------

Used by ``djstripe.middleware.SubscriptionPaymentMiddleware``

Rules:

* "(app_name)" means everything from this app is exempt
* "[namespace]" means everything with this name is exempt
* "namespace:name" means this namespaced URL is exempt
* "name" means this URL is exempt

Example:

.. code-block:: python

    DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS = (
        "(allauth)",  # anything in the django-allauth URLConf
        "[djstripe]",  # Anything in the djstripe app
        "products:detail",  # A ProductDetail view you want shown to non-payers
        "home",  # Site homepage
    )

DJSTRIPE_TRIAL_PERIOD_FOR_USER_CALLBACK (=None)
------------------------------------------------

TODO: Document!


DJSTRIPE_WEBHOOK_URL (=r"^webhook/$")
--------------------------------------

This is where you can set *Stripe.com* to send webhook response. You can set this to what you want to prevent unnecessary hijinks from unfriendly people.

As this is embedded in the URLConf, this must be a resolvable regular expression.