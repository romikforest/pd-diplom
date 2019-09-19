"""orders URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
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

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path, include

urlpatterns = [
    path('', include('rest_framework.urls', namespace='rest_framework')),
    path('admin/', admin.site.urls),
    path('api/v1/', include(('api.urls', 'api'), namespace='v1'), name='api_v1'),
    path('', lambda x: HttpResponseRedirect('/api/v1/'), name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT, name='media') \
  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

