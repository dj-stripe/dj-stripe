"""
Urls related to the djstripe app.

Wire this into the root URLConf this way::

    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    # url can be changed
    # Call to 'djstripe.urls' and 'namespace' must stay as is
"""

from django.urls import path

from . import views

app_name = "djstripe"

urlpatterns = [
    # Webhook
    path(
        "webhook/<uuid:uuid>/",
        views.ProcessWebhookView.as_view(),
        name="djstripe_webhook_by_uuid",
    ),
]
