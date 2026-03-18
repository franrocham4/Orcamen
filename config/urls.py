"""
URL configuration for Orcamen project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.dashboard.urls')),
    path('api/', include('apps.excel_processor.urls')),
]
