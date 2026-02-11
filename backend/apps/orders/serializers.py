from rest_framework import serializers
from apps.orders.models import Order, OrderItem

class OrderCreateItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    qty = serializers.IntegerField(min_value=1)

class OrderCreateSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(min_value=1)
    idempotency_key = serializers.CharField(max_length=128)
    observations = serializers.CharField(required=False, allow_blank=True, default='')
    items = OrderCreateItemSerializer(many=True)

class OrderItemOutSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='product.id')

    class Meta:
        model = OrderItem
        fields = ['product_id', 'qty', 'unit_price', 'subtotal']

class OrderOutSerializer(serializers.ModelSerializer):
    customer_id = serializers.IntegerField(source='customer.id')
    items = OrderItemOutSerializer(many=True)

    class Meta:
        model = Order
        fields = ['id', 'number', 'created_at', 'customer_id', 'status', 'total', 'observations', 'idempotency_key', 'items']
class OrderStatusPatchSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=16)
    note = serializers.CharField(required=False, allow_blank=True, default='')
