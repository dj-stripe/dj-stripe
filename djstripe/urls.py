# -*- coding: utf-8 -*-
"""
.. module:: djstripe.urls.

  :synopsis: dj-stripe - Urls related to the djstripe app.

  Wire this into the root URLConf this way::

      url(r'^stripe/', include('djstripe.urls', namespace="djstripe")),
      # url can be changed
      # Call to 'djstripe.urls' and 'namespace' must stay as is

  Call it from reverse()::

      reverse("djstripe:subscribe")

  Call from url tag::

      {% url 'djstripe:subscribe' %}

.. moduleauthor:: @pydanny
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import url

from . import settings as app_settings
from . import views


app_name = "djstripe"

urlpatterns = [
    # HTML views
    url(
        r"^subscribe/$",
        views.SubscribeView.as_view(),
        name="subscribe"
    ),
    url(
        r"^cancel/subscription/$",
        views.CancelSubscriptionView.as_view(),
        name="cancel_subscription"
    ),

    # Webhook
    url(
        app_settings.DJSTRIPE_WEBHOOK_URL,
        views.ProcessWebhookView.as_view(),
        name="webhook"
    ),
]
