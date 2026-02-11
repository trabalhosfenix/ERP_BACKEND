from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    MessageSerializer,
    RegisterSerializer,
    SessionLoginRequestSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


class IsAdminOrManager(permissions.BasePermission):
    message = "Apenas admin ou manager podem acessar este recurso."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=["admin", "manager"]).exists()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class SessionLoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]


class JWTRefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


class SessionAuthLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=SessionLoginRequestSerializer,
        responses={
            200: MessageSerializer,
            401: OpenApiResponse(response=MessageSerializer, description="Credenciais inválidas."),
        },
        tags=["auth"],
    )
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({"detail": "Credenciais inválidas."}, status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        return Response({"detail": "Sessão iniciada com sucesso."}, status=status.HTTP_200_OK)


class SessionLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: MessageSerializer},
        tags=["auth"],
    )
    def post(self, request):
        logout(request)
        return Response({"detail": "Sessão finalizada com sucesso."}, status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: UserSerializer},
        tags=["auth"],
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class UserManagementView(APIView):
    permission_classes = [IsAdminOrManager]

    @extend_schema(
        request=None,
        responses={200: UserSerializer(many=True)},
        tags=["auth"],
    )
    def get(self, request):
        users = User.objects.all().order_by("id")
        return Response(UserSerializer(users, many=True).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=UserCreateSerializer,
        responses={201: UserSerializer},
        tags=["auth"],
    )
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailManagementView(APIView):
    permission_classes = [IsAdminOrManager]

    @extend_schema(
        request=UserUpdateSerializer,
        responses={
            200: UserSerializer,
            404: OpenApiResponse(response=MessageSerializer, description="Usuário não encontrado."),
        },
        tags=["auth"],
    )
    def patch(self, request, user_id: int):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Usuário não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.update(user, serializer.validated_data)

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
