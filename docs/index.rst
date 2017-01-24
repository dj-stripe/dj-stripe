.. complexity documentation master file, created by
   sphinx-quickstart on Tue Jul  9 22:26:36 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Django + Stripe Made Easy
--------------------------------

* Subscription management
* Designed for easy implementation of post-registration subscription forms
* Single-unit purchases
* Works with Django >= 1.10
* Works with Python 3.6, 3.5, 3.4, 2.7
* Built-in migrations
* Dead-Easy installation
* Leverages the best of the 3rd party Django package ecosystem
* `djstripe` namespace so you can have more than one payments related app
* Documented
* 100% Tested
* Current API version (2017-06-05), in progress of being updated

Contents
---------

.. toctree::
   :caption: Getting Started

   installation

.. toctree::
   :caption: Usage

   usage/checking_customer_subscription
   usage/subscribing_customers.rst
   usage/one_off_charges.rst
   usage/restricting_access.rst
   usage/managing_subscriptions.rst
   usage/creating_invoices.rst
   usage/running_reports.rst
   usage/webhooks.rst
   usage/manually_syncing_with_stripe.rst
.. settings
.. cookbook

.. toctree::
   :caption: Reference
   :glob:

   models
   api/*

.. toctree::
   :caption: Project

   contributing
   authors
   history
   support

Constraints
------------

1. For stripe.com only
2. Only use or support well-maintained third-party libraries
3. For modern Python and Django
