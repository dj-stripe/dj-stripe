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
from __future__ import unicode_literals
from django.conf.urls import url

from . import settings as app_settings
from . import views


urlpatterns = [

    # HTML views
    url(
        r"^$",
        views.AccountView.as_view(),
        name="account"
    ),
    url(
        r"^subscribe/$",
        views.SubscribeView.as_view(),
        name="subscribe"
    ),
    url(
        r"^confirm/(?P<plan_id>.+)/$",
        views.ConfirmFormView.as_view(),
        name="confirm"
    ),
    url(
        r"^change/plan/$",
        views.ChangePlanView.as_view(),
        name="change_plan"
    ),
    url(
        r"^change/cards/$",
        views.ChangeCardView.as_view(),
        name="change_card"
    ),
    url(
        r"^cancel/subscription/$",
        views.CancelSubscriptionView.as_view(),
        name="cancel_subscription"
    ),
    url(
        r"^history/$",
        views.HistoryView.as_view(),
        name="history"
    ),


    # Web services
    url(
        r"^a/sync/history/$",
        views.SyncHistoryView.as_view(),
        name="sync_history"
    ),

    # Webhook
    url(
        app_settings.DJSTRIPE_WEBHOOK_URL,
        views.WebHook.as_view(),
        name="webhook"
    ),
]
