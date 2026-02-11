from django.contrib import admin
from django.urls import path, include
from apps.common.health import health

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health),
    path('api/v1/', include('apps.customers.urls')),
    path('api/v1/', include('apps.products.urls')),
    path('api/v1/', include('apps.orders.urls')),
]