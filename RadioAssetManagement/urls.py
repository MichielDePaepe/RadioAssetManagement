"""
URL configuration for RadioAssetManagement project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include
from RadioAssetManagement.views import index
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),  # voor taalwissel
]

urlpatterns += i18n_patterns(
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path('admin/', admin.site.urls),
    path('', index, name='home'),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('helpdesk/', include('helpdesk.urls', namespace='helpdesk')),
    path('radio/', include('radio.urls', namespace='radio')),
    path('organization/', include('organization.urls', namespace='organization')),
    path('taqto/', include('taqto.urls')),
    path('printer/', include('printer.urls')),
    path('astrid/', include('astrid.urls')),
    path('roip/', include("roip.urls", namespace='roip')),
    path('fireplan/', include("fireplan.urls", namespace='fireplan')),
)