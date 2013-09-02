Cookbook
========

This is a list of handy recipes that fall outside the domain of normal usage.

Customer User Model has_active_subscription method
--------------------------------------------------

Very useful for working inside of templates or other places where you need
to check the subscription status repeatedly. The `cached_property` decorator
caches the result of `has_active_subscription` for a object instance, optimizing
it for reuse.

.. code-block:: python

    # -*- coding: utf-8 -*-

    from django.contrib.auth.models import AbstractUser 
    from django.db import models
    from django.utils.functional import cached_property

    from djstripe.models import Customer


    class User(AbstractUser):

        """ Custom fields go here """

        def __str__(self):
            return self.username

        def __unicode__(self):
            return self.username

        @cached_property
        def has_active_subscription(self):
            """
            Helper method to check if a user has an active subscription.
            Throws improperlyConfigured if user.is_anonymous == True
            """
            if self.is_anonymous():
                return False
            customer, created = Customer.get_or_create(self)
            if created or not customer.has_active_subscription():
                return False
            return True


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

