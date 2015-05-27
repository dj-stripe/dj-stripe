# -*- coding: utf-8 -*-
"""
Wire this into the root URLConf this way::

    url(
        r'^api/v1/stripe/',
        include('djstripe.rest_urls', namespace="djstripe")
    ),
    # url can be changed
    # Call to 'djstripe.rest_urls' and 'namespace' must stay as is

"""

from __future__ import unicode_literals
from django.conf.urls import url

from . import restviews


urlpatterns = [

    # REST api
    url(
        r"^subscription/$",
        restviews.SubscriptionRestView.as_view(),
        name="subscription"
    ),

]
