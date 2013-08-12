=============================
dj-stripe
=============================

.. image:: https://badge.fury.io/py/dj-stripe.png
    :target: http://badge.fury.io/py/dj-stripe
    
.. image:: https://travis-ci.org/pydanny/dj-stripe.png?branch=master
        :target: https://travis-ci.org/pydanny/dj-stripe

.. image:: https://pypip.in/d/dj-stripe/badge.png
        :target: https://crate.io/packages/dj-stripe?version=latest


Django + Stripe for Humans

Documentation
-------------

The full documentation is at http://dj-stripe.rtfd.org.

Features
--------

* Subscription management
* Works with Django 1.5, 1.4
* Works with Python 3.3, 2.7, 2.6
* Dead-Easy installation (Done, just needs documentation)
* Single-unit purchases (forthcoming)


Quickstart
----------

Install dj-stripe:

.. code-block:: bash

    pip install dj-stripe

Add ``djstripe`` to your ``INSTALLED_APPS``:

.. code-block:: python

	INSTALLED_APPS +=(
	    "djstripe",
	)

Add the context processor to your ``TEMPLATE_CONTEXT_PROCESSORS``:

.. code-block:: python

    TEMPLATE_CONTEXT_PROCESSORS +=(
        'djstripe.context_processors.djstripe_settings',
    )

Add your stripe keys:

.. code-block:: python

    STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "<your publishable test key>")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "<your secret test key>")

Add some payment plans:

.. code-block:: python

    DJSTRIPE_PLANS = {
        "monthly": {
            "stripe_plan_id": "pro-monthly",
            "name": "Web App Pro ($24.99/month)",
            "description": "The monthly subscription plan to WebApp",
            "price": 2499,  # $24.99
            "currency": "usd",
            "interval": "month"
        },
        "yearly": {
            "stripe_plan_id": "pro-yearly",
            "name": "Web App Pro ($199/year)",
            "description": "The annual subscription plan to WebApp",
            "price": 19900,  # $199.00
            "currency": "usd",
            "interval": "year"
        }
    }

Add to the urls.py:

.. code-block:: python

	url(r'^payments/', include('djstripe.urls', namespace="djstripe")),
	
Run the commands::

	python manage.py syncdb

    python manage.py migrate  # if you are using South
	
	python manage.py djstripe_init_customers
	
	python manage.py djstripe_init_plans

If you haven't already, add the Bootstrap 3.0.0 JS and CSS to your base template:

.. code-block:: html

    <!-- Latest compiled and minified CSS -->
    <link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.0.0-rc1/css/bootstrap.min.css">
     
    <!-- Latest compiled and minified JavaScript -->
    <script src="//netdna.bootstrapcdn.com/bootstrap/3.0.0-rc1/js/bootstrap.min.js"></script>

Start up the webserver:

    * http://127.0.0.1:8000/payments/
