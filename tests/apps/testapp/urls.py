from django.conf.urls import include
from django.http import HttpResponse
from django.urls import path


def empty_view(request):
    return HttpResponse()


urlpatterns = [
    path("", empty_view, name="test_url_name"),
    path("djstripe/", include("djstripe.urls", namespace="djstripe")),
    path(
        "rest_djstripe/",
        include("djstripe.contrib.rest_framework.urls", namespace="rest_djstripe"),
    ),
]
