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


def _order_qs():
    return (
        Order.objects.select_related("customer")
        .prefetch_related("items", "items__product", "status_history")
    )


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(data: CreateOrderInput) -> Order:
        if not data.items:
            raise BusinessError("items não pode ser vazio")

        if any(it.qty <= 0 for it in data.items):
            raise BusinessError("qty deve ser maior que zero")

        customer = Customer.objects.filter(id=data.customer_id).first()
        if not customer:
            raise NotFoundError("cliente não encontrado")
        if not customer.is_active:
            raise ConflictError("cliente inativo")

        # Idempotência: Redis (best-effort)
        redis = get_redis()
        redis_key = f"idem:order:{customer.id}:{data.idempotency_key}"
        try:
            existing_id = redis.get(redis_key)
            if existing_id:
                return _order_qs().get(id=int(existing_id))
        except Exception:
            pass

        # Idempotência: banco (fonte de verdade)
        existing = _order_qs().filter(customer=customer, idempotency_key=data.idempotency_key).first()
        if existing:
            return existing

        product_ids = [it.product_id for it in data.items]

        # Lock pessimista dos produtos
        products = list(Product.objects.select_for_update().filter(id__in=product_ids))
        if len(products) != len(set(product_ids)):
            raise NotFoundError("um ou mais produtos não foram encontrados")

        products_by_id = {p.id: p for p in products}

        # Valida ativo + estoque suficiente (tudo ou nada)
        for it in data.items:
            product = products_by_id[it.product_id]
            if not product.is_active:
                raise ConflictError(f"produto {product.id} inativo")
            if product.stock_qty < it.qty:
                raise ConflictError(f"estoque insuficiente para SKU {product.sku}")

        # Criar pedido (race-safe via unique constraint)
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
            return _order_qs().get(customer=customer, idempotency_key=data.idempotency_key)

        total = Decimal("0.00")

        for it in data.items:
            product = products_by_id[it.product_id]
            unit_price = Decimal(product.price)
            subtotal = unit_price * Decimal(int(it.qty))

            product.stock_qty -= int(it.qty)
            product.save(update_fields=["stock_qty", "updated_at"])

            OrderItem.objects.create(
                order=order,
                product=product,
                qty=int(it.qty),
                unit_price=unit_price,
                subtotal=subtotal,
            )
            total += subtotal

        order.total = total
        order.save(update_fields=["total", "updated_at"])

        OrderStatusHistory.objects.create(
            order=order,
            from_status=OrderStatus.PENDENTE,
            to_status=OrderStatus.PENDENTE,
            changed_by=None,
            note="pedido criado",
        )

        # Redis pós-commit (não afeta transação)
        def _after_commit():
            try:
                redis.setex(redis_key, 60 * 60 * 24, order.id)
            except Exception:
                pass

        transaction.on_commit(_after_commit)

        return _order_qs().get(id=order.id)

    @staticmethod
    @transaction.atomic
    def change_status(order_id: int, new_status: str, user=None, note: str = "") -> Order:
        order = Order.objects.select_for_update().filter(id=order_id).first()
        if not order:
            raise NotFoundError("pedido não encontrado")

        if not can_transition(order.status, new_status):
            raise ConflictError(f"transição inválida {order.status} -> {new_status}")

        old = order.status
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])

        OrderStatusHistory.objects.create(
            order=order,
            from_status=old,
            to_status=new_status,
            changed_by=user,
            note=note or "",
        )

        def _after_commit():
            try:
                publish_order_status_changed(order, old, new_status, note or "")
            except Exception:
                pass

        transaction.on_commit(_after_commit)

        return _order_qs().get(id=order.id)

    @staticmethod
    @transaction.atomic
    def cancel_order(order_id: int, user=None, note: str = "") -> Order:
        order = Order.objects.select_for_update().filter(id=order_id).first()
        if not order:
            raise NotFoundError("pedido não encontrado")

        if order.status not in [OrderStatus.PENDENTE, OrderStatus.CONFIRMADO]:
            raise ConflictError("pedido não pode ser cancelado no status atual")

        items = list(order.items.select_related("product").all())

        for item in items:
            product = Product.objects.select_for_update().get(id=item.product_id)
            product.stock_qty += item.qty
            product.save(update_fields=["stock_qty", "updated_at"])

        old = order.status
        order.status = OrderStatus.CANCELADO
        order.save(update_fields=["status", "updated_at"])

        OrderStatusHistory.objects.create(
            order=order,
            from_status=old,
            to_status=OrderStatus.CANCELADO,
            changed_by=user,
            note=note or "pedido cancelado",
        )

        def _after_commit():
            try:
                publish_order_status_changed(order, old, OrderStatus.CANCELADO, note or "")
            except Exception:
                pass

        transaction.on_commit(_after_commit)

        # IMPORTANTE: não deletar o pedido (auditoria / histórico)
        return _order_qs().get(id=order.id)
