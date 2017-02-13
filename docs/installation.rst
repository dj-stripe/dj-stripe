============
Installation
============

Get the distribution
---------------------

At the command line::

    $ pip install dj-stripe


Configuration
---------------


Add ``djstripe`` to your ``INSTALLED_APPS``. You will also need the `sites` framework enabled.:

.. code-block:: python

    SITE_ID = 1

    INSTALLED_APPS += [
        'django.contrib.sites',
        # ...,
        "djstripe",
    ]

Add your Stripe keys:

.. code-block:: python

    STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "<your publishable key>")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "<your secret key>")

Add some payment plans:

.. code-block:: python

    DJSTRIPE_PLANS = {
        "monthly": {
            "stripe_plan_id": "pro-monthly",
            "name": "Web App Pro ($25/month)",
            "description": "The monthly subscription plan to WebApp",
            "price": 2500,  # $25.00
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

.. note:: Stripe Plan creation

    Not all properties listed in the plans above are used by Stripe - i.e 'description', which
    is used to display the plans description within specific templates.

    Although any arbitrary property you require can be added to each plan listed in DJ_STRIPE_PLANS,
    only specific properties are used by Stripe. The full list of required and optional arguments
    can be found here_.

.. _here: https://stripe.com/docs/api/python#create_plan

.. note:: The display order of the plans

    If you prefer the plans to appear (in views) in the order given in the
    `DJSTRIPE_PLANS` setting, use an `OrderedDict` from the `collections`
    module in the standard library, rather than an ordinary dict.

Add the following to the `urlpatterns` in your `urls.py` to expose payment views and the webhook endpoint:

.. code-block:: python

    url(r'^payments/', include('djstripe.urls', namespace="djstripe")),

.. note:: Using the inbuilt dj-stripe views

    There must be a `base.html` template on your template loader path with `javascript` and `content` blocks present
    for the dj-stripe views' templates to extend.

    .. code-block:: html

        {% block content %}{% endblock %}
        {% block javascript %}{% endblock %}

    If you haven't already, add JQuery and the Bootstrap 3.0.0+ JS and CSS to your base template as well:

    .. code-block:: html

        <!-- Latest compiled and minified CSS -->
        <link rel="stylesheet" href="https://netdna.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css">

        <!-- Optional theme -->
        <link rel="stylesheet" href="https://netdna.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap-theme.min.css">

        <!-- Latest JQuery (IE9+) -->
        <script src="//code.jquery.com/jquery-2.1.4.min.js"></script>

        <!-- Latest compiled and minified JavaScript -->
        <script src="https://netdna.bootstrapcdn.com/bootstrap/3.3.4/js/bootstrap.min.js"></script>

Run the commands::

    python manage.py migrate

    python manage.py djstripe_init_customers

Running Tests
--------------

Assuming the tests are run against PostgreSQL::

    createdb djstripe
    pip install -r tests/requirements.txt
    tox
