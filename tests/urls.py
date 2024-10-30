from django.contrib import admin
from django.http.response import HttpResponse
from django.urls import include, path

admin.autodiscover()


def empty_view(request):
    return HttpResponse()


urlpatterns = [
    path("home/", empty_view, name="home"),
    path("admin/", admin.site.urls),
    path("djstripe/", include("djstripe.urls", namespace="djstripe")),
    path("example/", include("tests.apps.example.urls")),
    path("testapp/", include("tests.apps.testapp.urls")),
    path(
        "testapp_namespaced/",
        include("tests.apps.testapp_namespaced.urls", namespace="testapp_namespaced"),
    ),
    # Represents protected content
    path("testapp_content/", include("tests.apps.testapp_content.urls")),
    # For testing fnmatches
    path("test_fnmatch/extra_text/", empty_view, name="test_fnmatch"),
]
