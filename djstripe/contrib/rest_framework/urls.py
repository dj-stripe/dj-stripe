"""
.. module:: dj-stripe.contrib.rest_framework.urls.

    :synopsis: URL routes for the dj-stripe REST API.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

Wire this into the root URLConf this way::

    path(
        'api/v1/stripe/',
        include('djstripe.contrib.rest_framework.urls', namespace="rest_djstripe")
    ),
    # url can be changed
    # Call to 'djstripe.contrib.rest_framework.urls' and 'namespace' must stay as is

"""

from django.urls import path

from . import views

app_name = "djstripe_rest_framework"

urlpatterns = [
    # Authenticated Endpoint for accessing list of Subscriptions
    path("subscriptions/",
         views.SubscriptionListView.as_view(),
         name="subscription-list"),

    # Authenticated Endpoint for accessing the detail of one Subscription.
    # Identification is made with Django's model "pk", but it could possibly be
    # extended to other (id, dj_stripeid...)
    path("subscriptions/<int:pk>",
         views.SubscriptionDetailView.as_view(),
         name="subscription-detail")
]
