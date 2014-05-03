from __future__ import unicode_literals
from django.conf.urls import patterns, url, include

from django.http import HttpResponse


def testview(request):
    return HttpResponse()

urlpatterns = patterns("",
    url(
        r"^$",
        testview,
        name="test_url_name"
    ),
    url(r"^djstripe/", include('djstripe.urls', namespace="djstripe")),
)