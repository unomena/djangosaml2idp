from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from . import views

app_name = 'example_sp'

urlpatterns = [
    url(r'^logout/$', auth_views.LogoutView.as_view()),
    url(r'^saml2/', include('djangosaml2.urls')),
    url(r'^admin/$', admin.site.urls),
    url(r'^$', views.IndexView.as_view()),
]
