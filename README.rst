=============================
dj-stripe
=============================

.. image:: https://badge.fury.io/py/dj-stripe.png
    :target: http://badge.fury.io/py/dj-stripe
    
.. image:: https://travis-ci.org/pydanny/dj-stripe.png?branch=master
        :target: https://travis-ci.org/pydanny/dj-stripe

.. image:: https://pypip.in/d/dj-stripe/badge.png
        :target: https://pypi.python.org/pypi/dj-stripe/


Django + Stripe Made Easy

Documentation
-------------

The full documentation is at http://dj-stripe.rtfd.org.

Features
--------

* Subscription management
* Designed for easy implementation of post-registration subscription forms
* Single-unit purchases (forthcoming)
* Works with Django 1.6, 1.5, 1.4
* Works with Python 3.3, 2.7, 2.6
* Works with Bootstrap 3
* Built-in South migrations
* Dead-Easy installation
* Leverages in the best of the 3rd party Django package ecosystem
* `djstripe` namespace so you can have more than one payments related app
* Documented (Making good progress)
* Tested (Making good progress)

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

If you haven't already, add JQuery and the Bootstrap 3.0.0 JS and CSS to your base template:

.. code-block:: html

    <!-- Latest compiled and minified CSS -->
    <link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap.min.css">

    <!-- Optional theme -->
    <link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap-theme.min.css">
    
    <!-- Latest JQuery -->
    <script src="//ajax.googleapis.com/ajax/libs/jquery/1.10.1/jquery.min.js"></script>

    <!-- Latest compiled and minified JavaScript -->
    <script src="//netdna.bootstrapcdn.com/bootstrap/3.0.0/js/bootstrap.min.js"></script>
    
Also, if you don't have it already, add a javascript block to your base.html file:

.. code-block:: html

    {% block javascript %}{% endblock %} 

Start up the webserver:

    * http://127.0.0.1:8000/payments/

Running the Tests
------------------

Assuming the tests are run against PostgreSQL::

    createdb djstripe
    pip install -r requirements_test.txt
    coverage run --source djstripe runtests.py
    coverage report -m

Follows Best Practices
======================

.. image:: http://twoscoops.smugmug.com/Two-Scoops-Press-Media-Kit/i-C8s5jkn/0/O/favicon-152.png
   :name: Two Scoops Logo
   :align: center
   :alt: Two Scoops of Django
   :target: http://twoscoopspress.org/products/two-scoops-of-django-1-6

This project follows best practices as espoused in `Two Scoops of Django: Best Practices for Django 1.6`_.

.. _`Two Scoops of Django: Best Practices for Django 1.6`: http://twoscoopspress.org/products/two-scoops-of-django-1-6

Similar Projects
----------------

* https://github.com/eldarion/django-stripe-payments - The project that dj-stripe forked. It's an awesome project and worth checking out.
* https://github.com/agiliq/merchant - A single charge payment processing system that also includes many other Gateways. Really nice but doesn't out-of-the-box handle the use case of subscription payments. 
* https://github.com/GoodCloud/django-zebra - One of the first stripe payment systems for Django. 

