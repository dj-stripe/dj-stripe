Cookbook
========

This is a list of handy recipes that fall outside the domain of normal usage.

Customer User Model has_active_subscription property
----------------------------------------------------

Very useful for working inside of templates or other places where you need
to check the subscription status repeatedly. The `cached_property` decorator
caches the result of `has_active_subscription` for a object instance, optimizing
it for reuse.

.. code-block:: python

    # -*- coding: utf-8 -*-

    from django.contrib.auth.models import AbstractUser
    from django.db import models
    from django.utils.functional import cached_property

    from djstripe.utils import subscriber_has_active_subscription


    class User(AbstractUser):

        """ Custom fields go here """

        def __str__(self):
            return self.username

        def __unicode__(self):
            return self.username

        @cached_property
        def has_active_subscription(self):
            """Checks if a user has an active subscription."""
            return subscriber_has_active_subscription(self)

Usage:

.. code-block:: html+django

    <ul class="actions">
    <h2>{{ object }}</h2>
    <!-- first use of request.user.has_active_subscription -->
    {% if request.user.has_active_subscription %}
        <p>
            <small>
                <a href="{% url 'things:update' %}">edit</a>
            </small>
        </p>
    {% endif %}
    <p>{{ object.description }}</p>

    <!-- second use of request.user.has_active_subscription -->
    {% if request.user.has_active_subscription %}
        <li>
            <a href="{% url 'places:create' %}">Add Place</a>
            <a href="{% url 'places:list' %}">View Places</a>
        </li>
    {% endif %}
    </ul>


Making individual purchases
---------------------------

On the subscriber's customer object, use the charge method to generate a Stripe charge. In this example, we're using the user with ID=1 as the subscriber.

.. code-block:: python

    from decimal import Decimal

    from django.contrib.auth import get_user_model

    from djstripe.models import Customer


    user = get_user_model().objects.get(id=1)

    customer, created = Customer.get_or_create(subscriber=user)

    amount = Decimal(10.00)
    customer.charge(amount)

Source code for the Customer.charge method is at https://github.com/dj-stripe/dj-stripe/blob/master/djstripe/models.py

REST API
--------

The subscriptions can be accessed through a REST API. Make sure you have
Django Rest Framework installed
(https://github.com/tomchristie/django-rest-framework).

The REST API endpoints require an authenticated user. GET will provide the
current subscription of the user. POST will create a new current subscription.
DELETE will cancel the current subscription, based on the settings.

- /subscription/ (GET)
    - input
        - None

    - output (200)

        - id (int)
        - created (date)
        - modified (date)
        - plan (string)
        - quantity (int)
        - start (date)
        - status (string)
        - cancel_at_period_end (boolean)
        - canceled_at (date)
        - current_period_end (date)
        - current_period_start (date)
        - ended_at (date)
        - trial_end (date)
        - trial_start (date)
        - amount (float)
        - customer (int)


- /subscription/ (POST)
    - input
        - stripe_token (string)
        - plan (string)
        - charge_immediately (boolean, optional)
          - Does not send an invoice to the Customer immediately

    - output (201)
        - stripe_token (string)
        - plan (string)

- /subscription/ (DELETE)
    - input
        - None

    - Output (204)
        - None

Not in the Cookbook?
=====================

Cartwheel Web provides `commercial support`_ for dj-stripe and other open source packages.

.. _commercial support: https://www.cartwheelweb.com/open-source-commercial-support/
