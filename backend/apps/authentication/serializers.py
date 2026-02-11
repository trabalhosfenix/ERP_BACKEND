from django.contrib.auth.models import Group, User
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
    profile = serializers.ChoiceField(choices=["admin", "manager", "operator", "viewer"], default="viewer")
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "first_name", "last_name", "profile"]

    def create(self, validated_data):
        profile = validated_data.pop("profile")
        user = User.objects.create_user(**validated_data)
        group, _ = Group.objects.get_or_create(name=profile)
        user.groups.add(group)
        return user


class UserSerializer(serializers.ModelSerializer):
    profiles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "profiles"]

    def get_profiles(self, obj):
        return list(obj.groups.values_list("name", flat=True))
