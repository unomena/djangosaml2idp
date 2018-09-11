from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf.urls import url, include
from . import views

app_name = 'example_idp'

urlpatterns = [
    url(r'^idp/$', include('djangosaml2idp.urls', namespace='djangosaml2')),
    url(r'^admin/$', admin.site.urls),
    url(
        r'^login/$',
        auth_views.LoginView.as_view(template_name='idp/login.html'),
        name='login'
    ),
    url(r'^logout/$', auth_views.LogoutView.as_view()),
    url(r'^$', views.IndexView.as_view()),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
