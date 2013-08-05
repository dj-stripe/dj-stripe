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

from . import settings as app_settings
from . import views


urlpatterns = patterns("",
    url(
        r"^subscribe/$",
        views.SubscribeFormView.as_view(),
        name="subscribe"
    ),
    url(
        r"^change/card/$",
        views.ChangeCardView.as_view(),
        name="change_card"
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
    url(
        app_settings.DJSTRIPE_WEBHOOK_URL,
        views.WebHook.as_view(),
        name="webhook"
    ),
)