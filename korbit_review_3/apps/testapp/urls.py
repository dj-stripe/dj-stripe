from django.http import HttpResponse
from django.urls import include, path


def empty_view(request):
    return HttpResponse()


urlpatterns = [
    path("", empty_view, name="test_url_name"),
    path("djstripe/", include("djstripe.urls", namespace="djstripe")),
]
