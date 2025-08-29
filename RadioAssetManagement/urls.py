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
from django.contrib import admin
from django.urls import path, include
from RadioAssetManagement.views import index

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='home'),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('helpdesk/', include('helpdesk.urls', namespace='helpdesk')),
    path('radio/', include('radio.urls', namespace='radio')),
    path('organization/', include('organization.urls', namespace='organization')),
    path('taqto/', include('taqto.urls')),
]
