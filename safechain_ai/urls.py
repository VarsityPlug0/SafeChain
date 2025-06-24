"""
URL configuration for aicryptovault project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from core import views
from core.admin import admin_site  # Import our custom admin site

def health_check(request):
    return HttpResponse("OK")

urlpatterns = [
    path('admin/', admin_site.urls),  # Use our custom admin site
    path('healthz/', health_check, name='health_check'),
    path('', include('core.urls')),
    path('admin_dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
