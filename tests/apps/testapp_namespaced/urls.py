from django.http import HttpResponse
from django.urls import path


def testview(request):
    return HttpResponse()


app_name = "testapp_namespaced"

urlpatterns = [path("", testview, name="test_url_namespaced")]
