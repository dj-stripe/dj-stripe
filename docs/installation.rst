============
Installation
============

Get the distribution
---------------------

At the command line::

    $ pip install dj-stripe


Configuration
---------------


Add ``djstripe`` to your ``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS += [
        'django.contrib.sites',
        # ...,
        "djstripe",
    ]

Add your Stripe keys and set the operating mode:

.. code-block:: python

    STRIPE_LIVE_PUBLIC_KEY = os.environ.get("STRIPE_LIVE_PUBLIC_KEY", "<your publishable key>")
    STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "<your secret key>")
    STRIPE_TEST_PUBLIC_KEY = os.environ.get("STRIPE_TEST_PUBLIC_KEY", "<your publishable key>")
    STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "<your secret key>")
    STRIPE_LIVE_MODE = <True or False>

Add some payment plans via the Stripe.com dashboard or the django ORM.

Add the following to the `urlpatterns` in your `urls.py` to expose the webhook endpoint:

.. code-block:: python

    url(r'^payments/', include('djstripe.urls', namespace="djstripe")),

Then tell Stripe about the webhook (Stripe webhook docs can be found `here <https://stripe.com/docs/webhooks>`_) using the full URL of your endpoint from the urls.py step above (e.g. ``https://yourwebsite.com/payments/webhook``).

Run the commands::

    python manage.py migrate

    python manage.py djstripe_init_customers

Running Tests
--------------

Assuming the tests are run against PostgreSQL::

    createdb djstripe
    pip install -r tests/requirements.txt
    tox
