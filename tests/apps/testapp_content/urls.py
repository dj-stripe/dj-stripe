"""
Represents protected content
"""

from __future__ import unicode_literals
from django.conf.urls import patterns, url

from django.http import HttpResponse


def testview(request):
    return HttpResponse()

urlpatterns = patterns("",
    url(
        r"^$",
        testview,
        name="test_url_content"
    ),
)
