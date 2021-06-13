"""
Urls related to the djstripe app.

Wire this into the root URLConf this way::

    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    # url can be changed
    # Call to 'djstripe.urls' and 'namespace' must stay as is
"""
from django.urls import re_path

from . import views
from .settings import djstripe_settings as app_settings

app_name = "djstripe"

urlpatterns = [
    # Webhook
    re_path(
        app_settings.DJSTRIPE_WEBHOOK_URL,
        views.ProcessWebhookView.as_view(),
        name="webhook",
    )
]
