from rest_framework.permissions import BasePermission


class ProfilePermission(BasePermission):
    """Controla acesso por perfil (grupos do Django) e método HTTP."""

    message = "Você não possui permissão para executar esta ação com seu perfil."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        allowed_profiles_by_method = getattr(view, "allowed_profiles_by_method", {})
        allowed_profiles = allowed_profiles_by_method.get(request.method)

        if not allowed_profiles:
            return True

        user_profiles = set(user.groups.values_list("name", flat=True))
        return bool(user_profiles.intersection(set(allowed_profiles)))
