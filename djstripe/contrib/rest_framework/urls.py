# -*- coding: utf-8 -*-
"""
.. module:: dj-stripe.contrib.rest_framework.urls.

    :synopsis: URL routes for the dj-stripe REST API.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

Wire this into the root URLConf this way::

    url(
        r'^api/v1/stripe/',
        include('djstripe.contrib.rest_framework.urls', namespace="rest_djstripe")
    ),
    # url can be changed
    # Call to 'djstripe.contrib.rest_framework.urls' and 'namespace' must stay as is

"""

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import url

from . import views


app_name = "djstripe_rest_framework"

urlpatterns = [
    # REST api
    url(
        r"^subscription/$",
        views.SubscriptionRestView.as_view(),
        name="subscription"
    ),

]
