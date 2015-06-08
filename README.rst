=============================
dj-stripe
=============================
Django + Stripe Made Easy

Badges
------

.. image:: https://img.shields.io/travis/pydanny/dj-stripe.svg?style=flat-square
        :target: https://travis-ci.org/pydanny/dj-stripe
.. image:: https://img.shields.io/codecov/c/github/pydanny/dj-stripe/master.svg?style=flat-square
        :target: http://codecov.io/github/pydanny/dj-stripe?branch=master
.. image:: https://img.shields.io/requires/github/pydanny/dj-stripe.svg?style=flat-square
        :target: https://requires.io/github/pydanny/dj-stripe/requirements/?branch=master
.. image:: https://img.shields.io/codacy/3c99e13eda1c4dea9f993b362e4ea816.svg?style=flat-square
        :target: https://www.codacy.com/app/kavanaugh-development/dj-stripe/dashboard

.. image:: https://img.shields.io/pypi/v/dj-stripe.svg?style=flat-square
        :target: https://pypi.python.org/pypi/dj-stripe
.. image:: https://img.shields.io/pypi/dw/dj-stripe.svg?style=flat-square
        :target: https://pypi.python.org/pypi/dj-stripe

.. image:: https://img.shields.io/github/issues/pydanny/dj-stripe.svg?style=flat-square
        :target: https://github.com/pydanny/dj-stripe/issues
.. image:: https://img.shields.io/github/license/pydanny/dj-stripe.svg?style=flat-square
        :target: https://github.com/pydanny/dj-stripe/blob/master/LICENSE

.. image:: https://badges.gitter.im/Join Chat.svg
        :target: https://gitter.im/pydanny/dj-stripe?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge


Documentation
-------------

The full documentation is at http://dj-stripe.rtfd.org.

Features
--------

* Subscription management
* Designed for easy implementation of post-registration subscription forms
* Single-unit purchases
* Works with Django 1.8, 1.7
* Works with Python 3.4, 2.7
* Works with Bootstrap 3
* Built-in migrations
* Dead-Easy installation
* Leverages the best of the 3rd party Django package ecosystem
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

Add your stripe keys:

.. code-block:: python

    STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "<your publishable key>")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "<your secret key>")

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

    python manage.py migrate
    
    python manage.py djstripe_init_customers
    
    python manage.py djstripe_init_plans

If you haven't already, add JQuery and the Bootstrap 3.0.0+ JS and CSS to your base template:

.. code-block:: html

    <!-- Latest compiled and minified CSS -->
    <link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css">

    <!-- Optional theme -->
    <link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap-theme.min.css">
    
    <!-- Latest JQuery (IE9+) -->
    <script src="//code.jquery.com/jquery-2.1.4.min.js"></script>

    <!-- Latest compiled and minified JavaScript -->
    <script src="//netdna.bootstrapcdn.com/bootstrap/3.3.4/js/bootstrap.min.js"></script>
    
Also, if you don't have it already, add a javascript block to your base.html file:

.. code-block:: html

    {% block javascript %}{% endblock %} 


Running the Tests
------------------

Assuming the tests are run against PostgreSQL::

    createdb djstripe
    pip install -r requirements_test.txt
    python runtests.py

Follows Best Practices
======================

.. image:: http://twoscoops.smugmug.com/Two-Scoops-Press-Media-Kit/i-C8s5jkn/0/O/favicon-152.png
   :name: Two Scoops Logo
   :align: center
   :alt: Two Scoops of Django
   :target: http://twoscoopspress.org/products/two-scoops-of-django-1-8

This project follows best practices as espoused in `Two Scoops of Django: Best Practices for Django 1.8`_.

.. _`Two Scoops of Django: Best Practices for Django 1.8`: http://twoscoopspress.org/products/two-scoops-of-django-1-8

Similar Projects
----------------

* https://github.com/eldarion/django-stripe-payments - The project that dj-stripe forked. It's an awesome project and worth checking out.
* https://github.com/agiliq/merchant - A single charge payment processing system that also includes many other Gateways. Really nice but doesn't out-of-the-box handle the use case of subscription payments. 
* https://github.com/GoodCloud/django-zebra - One of the first stripe payment systems for Django. 

