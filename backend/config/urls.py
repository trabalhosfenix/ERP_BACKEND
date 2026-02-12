from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from drf_spectacular.views import SpectacularRedocView

from apps.common.health import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health),
    path("templates/home", TemplateView.as_view(template_name="index.html"), name="home"),
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path("docs", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/", include("apps.authentication.urls")),
    path("api/v1/", include("apps.customers.urls")),
    path("api/v1/", include("apps.products.urls")),
    path("api/v1/", include("apps.orders.urls")),
    path("redoc", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
