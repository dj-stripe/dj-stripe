Migrating to dj-stripe
======================

There are a number of other Django powered stripe apps. This document explains how to migrate from them to **dj-stripe**.

django-stripe-payments
----------------------

Most of the settings can be used as is, but with these exceptions:

PAYMENT_PLANS vs DJSTRIPE_PLANS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**dj-stripe** allows for plans with decimal numbers. So you can have plans that are $9.99 instead of just $10. The price in a specific plan is therefore in cents rather than whole dollars

.. code-block:: pthon

    # settings.py

    # django-stripe-payments way
    PAYMENT_PLANS = {
        "monthly": {
            "stripe_plan_id": "pro-monthly",
            "name": "Web App Pro ($25/month)",
            "description": "The monthly subscription plan to WebApp",
            "price": 2500,  # $25.00
            "currency": "usd",
            "interval": "month"
        },
    }

    # dj-stripe way
    DJSTRIPE_PLANS = {
        "monthly": {
            "stripe_plan_id": "pro-monthly",
            "name": "Web App Pro ($25/month)",
            "description": "The monthly subscription plan to WebApp",
            "price": 2499,  # $24.99
            "currency": "usd",
            "interval": "month"
        },
    }

Migrating data
~~~~~~~~~~~~~~~

TODO