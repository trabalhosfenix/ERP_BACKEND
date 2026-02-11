from rest_framework import serializers
from .models import Customer

class CustomerCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'cpf_cnpj', 'email', 'phone', 'address', 'is_active', 'created_at']

class CustomerDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'cpf_cnpj', 'email', 'phone', 'address', 'is_active', 'created_at', 'updated_at']
