from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.soft_delete import SoftDeleteModel
from apps.customers.models import Customer
from apps.products.models import Product
from .domain.enums import OrderStatus


class Order(SoftDeleteModel):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    number = models.CharField(max_length=32, unique=True)
    status = models.CharField(max_length=16, choices=OrderStatus.choices, default=OrderStatus.PENDENTE, db_index=True)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    observations = models.TextField(blank=True, default="")
    idempotency_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        constraints = [
            models.UniqueConstraint(fields=["customer", "idempotency_key"], name="uq_order_customer_idempotency"), # garante que o mesmo cliente não crie múltiplas ordens com a mesma chave de idempotência
        ]
        indexes = [models.Index(fields=["customer", "created_at"]), models.Index(fields=["status"])] # índices para consultas frequentes por cliente, data de criação e status


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    qty = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        db_table = "order_items"
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["product"]),
        ]


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=16, choices=OrderStatus.choices)
    to_status = models.CharField(max_length=16, choices=OrderStatus.choices)
    changed_at = models.DateTimeField(default=timezone.now)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "order_status_history"
        indexes = [
            models.Index(fields=["order", "changed_at"]),
        ]


class OrderDomainEvent(models.Model):
    event_type = models.CharField(max_length=64)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="domain_events")
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_domain_events"
