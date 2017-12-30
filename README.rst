=============================
dj-stripe
=============================
Django + Stripe Made Easy

Badges
------

.. image:: https://img.shields.io/travis/dj-stripe/dj-stripe.svg?style=flat-square
        :target: https://travis-ci.org/dj-stripe/dj-stripe
.. image:: https://img.shields.io/codecov/c/github/dj-stripe/dj-stripe.svg?style=flat-square
        :target: http://codecov.io/github/dj-stripe/dj-stripe
.. image:: https://pyup.io/repos/github/dj-stripe/dj-stripe/shield.svg
        :target: https://pyup.io/repos/github/dj-stripe/dj-stripe/
.. image:: https://img.shields.io/codacy/grade/3c99e13eda1c4dea9f993b362e4ea816.svg?style=flat-square
        :target: https://www.codacy.com/app/kavdev/dj-stripe

.. image:: https://img.shields.io/pypi/v/dj-stripe.svg?style=flat-square
        :target: https://pypi.python.org/pypi/dj-stripe
.. image:: https://img.shields.io/pypi/dw/dj-stripe.svg?style=flat-square
        :target: https://pypi.python.org/pypi/dj-stripe

.. image:: https://img.shields.io/github/issues/dj-stripe/dj-stripe.svg?style=flat-square
        :target: https://github.com/dj-stripe/dj-stripe/issues
.. image:: https://img.shields.io/github/license/dj-stripe/dj-stripe.svg?style=flat-square
        :target: https://github.com/dj-stripe/dj-stripe/blob/master/LICENSE


Documentation
-------------

The full documentation is at http://dj-stripe.rtfd.org.

Features
--------

* Subscription management
* Designed for easy implementation of post-registration subscription forms
* Single-unit purchases
* Works with Django >= 1.11
* Works with Python 3.6, 3.5, 3.4, 2.7
* Built-in migrations
* Dead-Easy installation
* Leverages the best of the 3rd party Django package ecosystem
* `djstripe` namespace so you can have more than one payments related app
* Documented
* 100% Tested
* Current API version (2017-06-05), in progress of being updated

Constraints
------------

1. For stripe.com only
2. Only use or support well-maintained third-party libraries
3. For modern Python and Django


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
    STRIPE_LIVE_MODE = <True or False>

Add some payment plans via the Stripe.com dashboard or the django ORM.

Add to the urls.py:

.. code-block:: python

    url(r'^payments/', include('djstripe.urls', namespace="djstripe")),

Then tell Stripe about the webhook (Stripe webhook docs can be found `here <https://stripe.com/docs/webhooks>`_) using the full URL of your endpoint from the urls.py step above (e.g. ``https://yourwebsite.com/payments/webhook``).

Run the commands::

    python manage.py migrate

    python manage.py djstripe_init_customers


Running the Tests
------------------

Assuming the tests are run against PostgreSQL::

    createdb djstripe
    pip install tox
    tox

Follows Best Practices
======================

.. image:: http://twoscoops.smugmug.com/Two-Scoops-Press-Media-Kit/i-C8s5jkn/0/O/favicon-152.png
   :name: Two Scoops Logo
   :align: center
   :alt: Two Scoops of Django
   :target: http://twoscoopspress.org/products/two-scoops-of-django-1-11

This project follows best practices as espoused in `Two Scoops of Django: Best Practices for Django 1.11`_.

.. _`Two Scoops of Django: Best Practices for Django 1.11`: http://twoscoopspress.org/products/two-scoops-of-django-1-11
