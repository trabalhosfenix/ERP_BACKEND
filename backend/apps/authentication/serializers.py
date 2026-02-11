from django.contrib.auth.models import Group, User
from rest_framework import serializers


PROFILE_CHOICES = ["admin", "manager", "operator", "viewer"]


class RegisterSerializer(serializers.ModelSerializer):
    profile = serializers.ChoiceField(choices=PROFILE_CHOICES, default="viewer")
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
        fields = ["id", "username", "email", "first_name", "last_name", "is_active", "profiles"]

    def get_profiles(self, obj):
        return list(obj.groups.values_list("name", flat=True))


class UserCreateSerializer(serializers.ModelSerializer):
    profile = serializers.ChoiceField(choices=PROFILE_CHOICES)
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "first_name", "last_name", "profile", "is_active"]

    def create(self, validated_data):
        profile = validated_data.pop("profile")
        user = User.objects.create_user(**validated_data)
        group, _ = Group.objects.get_or_create(name=profile)
        user.groups.set([group])
        return user


class UserUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    profile = serializers.ChoiceField(choices=PROFILE_CHOICES, required=False)

    def update(self, instance, validated_data):
        profile = validated_data.pop("profile", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if profile:
            group, _ = Group.objects.get_or_create(name=profile)
            instance.groups.set([group])

        return instance

    def create(self, validated_data):
        raise NotImplementedError
