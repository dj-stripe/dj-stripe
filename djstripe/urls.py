"""
Urls related to the djstripe app.

Wire this into the root URLConf this way::

	url(r"^stripe/", include("djstripe.urls", namespace="djstripe")),
	# url can be changed
	# Call to 'djstripe.urls' and 'namespace' must stay as is

Call it from reverse()::

	reverse("djstripe:subscribe")

Call from url tag::

	{% url "djstripe:subscribe" %}
"""
from django.conf.urls import url

from . import settings as app_settings
from . import views

app_name = "djstripe"

urlpatterns = [
	# Webhook
	url(
		app_settings.DJSTRIPE_WEBHOOK_URL, views.ProcessWebhookView.as_view(), name="webhook"
	)
]
