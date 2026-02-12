from rest_framework import serializers
from .models import Product

class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'sku', 'name', 'description', 'price', 'stock_qty', 'is_active', 'created_at']

class ProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'sku', 'name', 'description', 'price', 'stock_qty', 'is_active', 'created_at', 'updated_at']

class ProductStockPatchSerializer(serializers.Serializer):
    stock_qty = serializers.IntegerField(min_value=0)
