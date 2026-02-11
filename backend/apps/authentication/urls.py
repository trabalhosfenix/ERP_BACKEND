from django.urls import path

from .views import (
    JWTRefreshView,
    MeView,
    RegisterView,
    SessionAuthLoginView,
    SessionLoginView,
    SessionLogoutView,
)

urlpatterns = [
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/jwt/login", SessionLoginView.as_view(), name="auth-jwt-login"),
    path("auth/jwt/refresh", JWTRefreshView.as_view(), name="auth-jwt-refresh"),
    path("auth/session/login", SessionAuthLoginView.as_view(), name="auth-session-login"),
    path("auth/session/logout", SessionLogoutView.as_view(), name="auth-session-logout"),
    path("auth/me", MeView.as_view(), name="auth-me"),
]
