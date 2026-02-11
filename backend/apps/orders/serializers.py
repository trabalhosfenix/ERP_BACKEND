from rest_framework import serializers

from apps.orders.domain.enums import OrderStatus
from apps.orders.models import Order, OrderItem, OrderStatusHistory


class OrderCreateItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    qty = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(min_value=1)
    idempotency_key = serializers.CharField(max_length=128)
    observations = serializers.CharField(required=False, allow_blank=True, default="")
    items = OrderCreateItemSerializer(many=True)


class OrderItemOutSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id")

    class Meta:
        model = OrderItem
        fields = ["product_id", "qty", "unit_price", "subtotal"]


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ["from_status", "to_status", "changed_at", "note"]


class OrderOutSerializer(serializers.ModelSerializer):
    customer_id = serializers.IntegerField(source="customer.id")
    items = OrderItemOutSerializer(many=True)
    status_history = OrderStatusHistorySerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "number",
            "created_at",
            "customer_id",
            "status",
            "total",
            "observations",
            "idempotency_key",
            "items",
            "status_history",
        ]


class OrderStatusPatchSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices)
    note = serializers.CharField(required=False, allow_blank=True, default="")

class OrderDetailSerializer(OrderOutSerializer):
    pass


class OrderListSerializer(OrderOutSerializer):
    pass



