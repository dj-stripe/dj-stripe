"""
Represents protected content
"""

from __future__ import unicode_literals
from django.conf.urls import url

from django.http import HttpResponse


def testview(request):
    return HttpResponse()

urlpatterns = [
    url(
        r"^$",
        testview,
        name="test_url_content"
    ),
]
