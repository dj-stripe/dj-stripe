from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import include, url
from django.http import HttpResponse


def empty_view(request):
    return HttpResponse()


urlpatterns = [
    url(
        r"^$",
        empty_view,
        name="test_url_name"
    ),
    url(r"^djstripe/", include('djstripe.urls', namespace="djstripe")),
    url(
        r"^rest_djstripe/",
        include('djstripe.contrib.rest_framework.urls', namespace="rest_djstripe")
    ),
]
