from __future__ import unicode_literals
from django.conf.urls import url

from django.http import HttpResponse


def testview(request):
    return HttpResponse()


app_name = "testapp_namespaced"

urlpatterns = [
    url(
        r"^$",
        testview,
        name="test_url_namespaced",
    ),
]
