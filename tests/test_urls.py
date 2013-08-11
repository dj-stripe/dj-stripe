# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, include, url


from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',

    url(r'^admin/', include(admin.site.urls)),
    url(r'^djstripe/', include('djstripe.urls',
            namespace="djstripe", app_name="djstripe")),
    url(r'^testapp/', include('tests.apps.testapp.urls')),
    url(
        r'^testapp_namespaced/',
        include('tests.apps.testapp_namespaced.urls',
        namespace="testapp_namespaced",
        app_name="testapp_namespaced")),

    # Represents protected content
    url(r'^testapp_content/', include('tests.apps.testapp_content.urls')),
)

