from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('pagamentos/', include('apps.pagamentos.urls')),
]
