"""
Wire this into the root URLConf this way::

    url(r'^stripe/', include('djstripe.urls', namespace="djstripe")),
    # url can be changed
    # namespace can be changed
    # Call to 'djstripe.urls' must stay as is

Call it from reverse()::

    reverse("djstripe:subscribe")

Call from url tag::

    {% url 'djstripe:subscribe' %}

"""

from __future__ import unicode_literals
from django.conf.urls import patterns, url

from djstripe import views


urlpatterns = patterns("",
    url(
        r"^subscribe/$",
        views.SubscribeView.as_view(),
        name="subscribe"
    ),
    url(
        r"^change/card/$",
        views.ChangeCardView.as_view(),
        name="change_card"
    ),
    url(
        r"^change/plan/$",
        views.ChangePlanView.as_view(),
        name="change_plan"
    ),
    url(
        r"^cancel/$",
        views.CancelView.as_view(),
        name="cancel"
    ),
    url(
        r"^history/$",
        views.HistoryView.as_view(),
        name="history"
    ),
)