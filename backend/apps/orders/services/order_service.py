from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.common.redis import get_redis
from apps.customers.models import Customer
from apps.orders.domain.enums import OrderStatus
from apps.orders.domain.events import publish_order_status_changed
from apps.orders.domain.transitions import can_transition
from apps.orders.models import Order, OrderItem, OrderStatusHistory
from apps.products.models import Product


@dataclass(frozen=True)
class CreateOrderItemInput:
    product_id: int
    qty: int


@dataclass(frozen=True)
class CreateOrderInput:
    customer_id: int
    idempotency_key: str
    observations: str
    items: List[CreateOrderItemInput]


class BusinessError(Exception):
    status_code = 400


class NotFoundError(BusinessError):
    status_code = 404


class ConflictError(BusinessError):
    status_code = 409


def _generate_order_number() -> str:
    return timezone.now().strftime("%Y%m%d%H%M%S%f")


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(data: CreateOrderInput) -> tuple[Order, bool]:
        if not data.items:
            raise BusinessError("items cannot be empty")

        customer = Customer.objects.filter(id=data.customer_id).first()
        if not customer:
            raise NotFoundError("customer not found")
        if not customer.is_active:
            raise ConflictError("customer inactive")

        redis = get_redis()
        redis_key = f"idem:order:{customer.id}:{data.idempotency_key}"
        try:
            existing_id = redis.get(redis_key)
            if existing_id:
                return Order.objects.prefetch_related("items").get(id=int(existing_id)), False
        except Exception:
            pass

        existing = Order.objects.filter(customer=customer, idempotency_key=data.idempotency_key).first()
        if existing:
            return existing, False

        product_ids = [it.product_id for it in data.items]
        if any(it.qty <= 0 for it in data.items):
            raise BusinessError("qty must be greater than zero")

        products = list(Product.objects.select_for_update().filter(id__in=product_ids))
        if len(products) != len(set(product_ids)):
            raise NotFoundError("one or more products were not found")
        products_by_id = {p.id: p for p in products}

        for it in data.items:
            product = products_by_id[it.product_id]
            if not product.is_active:
                raise ConflictError(f"product {product.id} is inactive")
            if product.stock_qty < it.qty:
                raise ConflictError(f"insufficient stock for SKU {product.sku}")

        try:
            order = Order.objects.create(
                customer=customer,
                number=_generate_order_number(),
                status=OrderStatus.PENDENTE,
                observations=data.observations or "",
                idempotency_key=data.idempotency_key,
                total=Decimal("0.00"),
            )
        except IntegrityError:
            existing = Order.objects.get(customer=customer, idempotency_key=data.idempotency_key)
            return existing, False

        total = Decimal("0.00")
        for it in data.items:
            product = products_by_id[it.product_id]
            subtotal = Decimal(product.price) * Decimal(it.qty)
            product.stock_qty -= it.qty
            product.save(update_fields=["stock_qty", "updated_at"])
            OrderItem.objects.create(order=order, product=product, qty=it.qty, unit_price=product.price, subtotal=subtotal)
            total += subtotal

        order.total = total
        order.save(update_fields=["total", "updated_at"])
        OrderStatusHistory.objects.create(order=order, from_status=OrderStatus.PENDENTE, to_status=OrderStatus.PENDENTE, note="order created")

        try:
            redis.setex(redis_key, 60 * 60 * 24, order.id)
        except Exception:
            pass
        return order, True

    @staticmethod
    @transaction.atomic
    def change_status(order_id: int, new_status: str, user=None, note: str = "") -> Order:
        order = Order.objects.select_for_update().filter(id=order_id).first()
        if not order:
            raise NotFoundError("order not found")

        if not can_transition(order.status, new_status):
            raise ConflictError(f"invalid status transition {order.status} -> {new_status}")

        old = order.status
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(order=order, from_status=old, to_status=new_status, changed_by=user, note=note)
        publish_order_status_changed(order, old, new_status, note)
        return order

    @staticmethod
    @transaction.atomic
    def cancel_order(order_id: int, user=None, note: str = "") -> Order:
        order = Order.objects.select_for_update().filter(id=order_id).first()
        if not order:
            raise NotFoundError("order not found")
        if order.status not in [OrderStatus.PENDENTE, OrderStatus.CONFIRMADO]:
            raise ConflictError("order cannot be canceled in current status")

        for item in order.items.select_related("product"):
            product = Product.objects.select_for_update().get(id=item.product_id)
            product.stock_qty += item.qty
            product.save(update_fields=["stock_qty", "updated_at"])

        old = order.status
        order.status = OrderStatus.CANCELADO
        order.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(order=order, from_status=old, to_status=OrderStatus.CANCELADO, changed_by=user, note=note or "canceled")
        publish_order_status_changed(order, old, OrderStatus.CANCELADO, note)
        order.delete()
        return order
