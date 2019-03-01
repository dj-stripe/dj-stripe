=========
dj-stripe
=========

.. image:: https://travis-ci.org/dj-stripe/dj-stripe.png
   :alt: Build Status
   :target: https://travis-ci.org/dj-stripe/dj-stripe

Stripe Models for Django.


Introduction
------------

dj-stripe implements all of the Stripe models, for Django.
Set up your webhook and start receiving model updates.
You will then have a copy of all the Stripe models available in Django models, no API traffic required!

The full documentation is available here: https://dj-stripe.readthedocs.io/

Features
--------

* Subscriptions
* Individual charges
* Stripe Sources
* Stripe v2 and v3 support
* Supports Stripe API `2019-02-19`

Requirements
------------

* Django >= 2.0
* Python >= 3.4
* Supports Stripe exclusively. For PayPal, see `dj-paypal <https://github.com/HearthSim/dj-paypal>`_ instead.
* PostgreSQL engine (recommended): >= 9.4
* MySQL engine: MariaDB >= 10.2 or MySQL >= 5.7


Quickstart
----------

Install dj-stripe:

.. code-block:: bash

    pip install dj-stripe

Add ``djstripe`` to your ``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS =(
        ...
        "djstripe",
        ...
    )

Add your Stripe keys and set the operating mode:

.. code-block:: python

    STRIPE_LIVE_PUBLIC_KEY = os.environ.get("STRIPE_LIVE_PUBLIC_KEY", "<your publishable key>")
    STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "<your secret key>")
    STRIPE_TEST_PUBLIC_KEY = os.environ.get("STRIPE_TEST_PUBLIC_KEY", "<your publishable key>")
    STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "<your secret key>")
    STRIPE_LIVE_MODE = False  # Change to True in production

Add some payment plans via the Stripe.com dashboard.

Add to urls.py:

.. code-block:: python

    path("stripe/", include("djstripe.urls", namespace="djstripe")),

Then tell Stripe about the webhook (Stripe webhook docs can be found `here <https://stripe.com/docs/webhooks>`_) using the full URL of your endpoint from the urls.py step above (e.g. ``https://example.com/stripe/webhook``).

Run the commands::

    python manage.py migrate

    python manage.py djstripe_init_customers

    python manage.py djstripe_sync_plans_from_stripe


Running the Tests
------------------

Assuming the tests are run against PostgreSQL::

    createdb djstripe
    pip install tox
    tox

Follows Best Practices
======================

.. image:: https://twoscoops.smugmug.com/Two-Scoops-Press-Media-Kit/i-C8s5jkn/0/O/favicon-152.png
   :name: Two Scoops Logo
   :align: center
   :alt: Two Scoops of Django
   :target: https://www.twoscoopspress.org/products/two-scoops-of-django-1-11

This project follows best practices as espoused in `Two Scoops of Django: Best Practices for Django 1.11`_.

.. _`Two Scoops of Django: Best Practices for Django 1.11`: https://twoscoopspress.org/products/two-scoops-of-django-1-11
