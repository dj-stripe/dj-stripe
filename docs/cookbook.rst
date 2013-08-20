Cookbook
========

This is a list of handy recipes that fall outside the domain of normal usage.

Getting a CHOICES-style list of plans
-------------------------------------

It's a common use case that you want to present internally the list of plans available to a user. To do this, just import `djstripe.settings.PLAN_CHOICES`:

.. code-block:: python

    #!/usr/bin/env python
    # -*- coding: utf-8 -*-

    from django.contrib.auth.models import AbstractUser
    from django.db import models
    from django.utils.translation import ugettext_lazy as _

    from djstripe.safe_settings import PLAN_CHOICES


    class User(AbstractUser):

        plan = models.CharField(_("plan"), choices=PLAN_CHOICES)

        def __unicode__(self):
            return self.username

