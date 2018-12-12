from django.conf.urls import include, url
from django.contrib import admin
from django.http.response import HttpResponse

admin.autodiscover()


def empty_view(request):
	return HttpResponse()


urlpatterns = [
	url(r"^home/", empty_view, name="home"),
	url(r"^admin/", admin.site.urls),
	url(r"^djstripe/", include("djstripe.urls", namespace="djstripe")),
	url(r"^testapp/", include("tests.apps.testapp.urls")),
	url(
		r"^testapp_namespaced/",
		include("tests.apps.testapp_namespaced.urls", namespace="testapp_namespaced"),
	),
	# Represents protected content
	url(r"^testapp_content/", include("tests.apps.testapp_content.urls")),
	# For testing fnmatches
	url(r"test_fnmatch/extra_text/$", empty_view, name="test_fnmatch"),
	# Default for DJSTRIPE_SUBSCRIPTION_REDIRECT
	url(r"subscribe/$", empty_view, name="test_url_subscribe"),
]
