============
Installation
============

Get the distribution
---------------------

At the command line::

    $ easy_install dj-stripe

Or, if you have virtualenvwrapper installed::

    $ mkvirtualenv dj-stripe
    $ pip install dj-stripe


Or for development, first fork it and then:

    $ git clone https://github.com/<yourname>/dj-stripe/
    $ python setup.py develop


Configuration
---------------


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
            "price": 19900,  # $19900
            "currency": "usd",
            "interval": "year"
        }
    }

Add to the urls.py::

    url(r'^payments/', include('djstripe.urls', namespace="djstripe")),
    
Run the commands::

    python manage.py syncdb
    
    python manage.py djstripe_init_customers
    
    python manage.py djstripe_init_plans

Start up the webserver:

    * http://127.0.0.1:8000/payments/

Running Tests
--------------

::

    pip install -r requirements_text.txt
    coverage run --source djstripe runtests.py
    coverage report -m