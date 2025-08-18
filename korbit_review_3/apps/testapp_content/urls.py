"""
Represents protected content
"""

from django.http import HttpResponse
from django.urls import path


def testview(request):
    return HttpResponse()


urlpatterns = [path("", testview, name="test_url_content")]
