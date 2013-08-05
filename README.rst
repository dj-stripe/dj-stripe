=============================
dj-stripe
=============================

.. image:: https://badge.fury.io/py/dj-stripe.png
    :target: http://badge.fury.io/py/dj-stripe
    
.. image:: https://travis-ci.org/pydanny/dj-stripe.png?branch=master
        :target: https://travis-ci.org/pydanny/dj-stripe

.. image:: https://pypip.in/d/dj-stripe/badge.png
        :target: https://crate.io/packages/dj-stripe?version=latest


A Django app for Stripe

Documentation
-------------

The full documentation is at http://dj-stripe.rtfd.org.

Quickstart
----------

Install dj-stripe::

    pip install dj-stripe

settings.py::

	# settings.py
	INSTALLED_APPS +=(
	    "djstripe",
	)

urls.py::

	url(r'^stripe/', include('djstripe.urls', namespace="djstripe")),
	
Run the commands::

	python manage.py syncdb
	
	python manage.py djstripe_init_customers
	
	python manage.py djstripe_init_plans

Running Tests
--------------

::

    pip install -r requirements_text.txt
    python runtests.py

Features
--------

* TODO

