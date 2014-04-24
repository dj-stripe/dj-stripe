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


    class User(AbstractUser):

        """ Custom fields go here """

        def __str__(self):
            return self.username

        def __unicode__(self):
            return self.username

        @cached_property
        def has_active_subscription(self):
            """
            Helper property to check if a user has an active subscription.
            """
            # Anonymous users return false
            if self.is_anonymous():
                return False

            # Import placed here to avoid circular imports
            from djstripe.models import Customer

            # Get or create the customer object
            customer, created = Customer.get_or_create(self)

            # If new customer, return false
            # If existing customer but inactive return false
            if created or not customer.has_active_subscription():
                return False

            # Existing, valid customer so return true
            return True

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


Adding a custom plan that is outside of stripe
-----------------------------------------------
 
Sometimes you want a custom plan for per-customer billing. Or perhaps you are providing a special free-for-open-source plan. In which case, `djstripe.safe_settings.PLAN_CHOICES` is your friend:

.. code-block:: python

    #!/usr/bin/env python
    # -*- coding: utf-8 -*-

    from django.contrib.auth.models import AbstractUser
    from django.db import models
    from django.utils.translation import ugettext_lazy as _

    from djstripe.safe_settings import PLAN_CHOICES
    from djstripe.signals import subscription_made

    CUSTOM_CHOICES = (
        ("custom", "Custom"),
    )

    CUSTOMIZED_CHOICES = PLAN_CHOICES + CUSTOM_CHOICES

    class User(AbstractUser):

        plan = models.CharField(_("plan"), choices=CUSTOMIZED_CHOICES)

        def __unicode__(self):
            return self.username


    @receiver(subscription_made)
    def my_callback(sender, **kwargs):
        # Updates the User record any time the subscription is changed.
        user = User.objects.get(
                    customer__stripe_id=kwargs['stripe_response'].customer
        )

        # Only update users with non-custom choices
        if user.plan in [x[0] for x in PLAN_CHOICES]:
            user.plan = kwargs['plan']
            user.save()

Making individual purchases
---------------------------

On the user's customer object, use the charge method to generate a Stripe charge. You'll need to have already captured the user's ``stripe_id``.

.. code-block:: python

    from decimal import Decimal

    from django.contrib.auth import get_user_model

    from djstripe.models import Customer

    User = get_user_model()

    customer, created = Customer.get_or_create(user)

    amount = Decimal(10.00)
    customer.charge(amount)

Source code for the Customer.charge method is at https://github.com/pydanny/dj-stripe/blob/master/djstripe/models.py#L561-L580