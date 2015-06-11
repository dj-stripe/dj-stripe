# -*- coding: utf-8 -*-
"""
Wire this into the root URLConf this way::

    url(
        r'^api/v1/stripe/',
        include('djstripe.contrib.rest_framework.urls', namespace="rest_djstripe")
    ),
    # url can be changed
    # Call to 'djstripe.contrib.rest_framework.urls' and 'namespace' must stay as is

"""

from __future__ import unicode_literals
from django.conf.urls import url

from . import views


urlpatterns = [

    # REST api
    url(
        r"^subscription/$",
        views.SubscriptionRestView.as_view(),
        name="subscription"
    ),

]
