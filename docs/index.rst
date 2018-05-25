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
   usage/cookbook

.. toctree::
   :caption: Reference
   :glob:

   reference/context_managers.rst
   reference/decorators.rst
   reference/enums.rst
   reference/managers.rst
   reference/middleware.rst
   reference/models.rst
   reference/settings.rst
   reference/utils.rst

.. toctree::
   :caption: Project

   project/contributing.rst
   project/authors.rst
   project/history.rst
   project/support.rst

Constraints
------------

1. For stripe.com only
2. Only use or support well-maintained third-party libraries
3. For modern Python and Django