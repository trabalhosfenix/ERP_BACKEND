from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List
from django.db import transaction
from django.utils import timezone

from apps.customers.models import Customer
from apps.products.models import Product
from apps.orders.models import Order, OrderItem, OrderStatusHistory
from apps.orders.domain.enums import OrderStatus

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
    now = timezone.now()
    return now.strftime('%Y%m%d%H%M%S%f')

class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(data: CreateOrderInput) -> Order:
        if not data.items:
            raise BusinessError('items não pode ser vazio')

        customer = Customer.objects.filter(id=data.customer_id).first()
        if not customer:
            raise NotFoundError('Cliente não encontrado')
        if not customer.is_active:
            raise ConflictError('Cliente inativo')

        existing = Order.objects.filter(customer_id=customer.id, idempotency_key=data.idempotency_key).first()
        if existing:
            return existing

        product_ids: List[int] = []
        for it in data.items:
            if it.qty <= 0:
                raise BusinessError('Quantidade deve ser maior que zero')
            product_ids.append(it.product_id)

        products = list(Product.objects.select_for_update().filter(id__in=product_ids))
        if len(products) != len(set(product_ids)):
            raise NotFoundError('Um ou mais produtos não foram encontrados')

        products_by_id = {p.id: p for p in products}

        for it in data.items:
            p = products_by_id[it.product_id]
            if not p.is_active:
                raise ConflictError(f'Produto {p.id} inativo')
            if p.stock_qty < it.qty:
                raise ConflictError(f'Estoque insuficiente para produto {p.sku}')

        order = Order.objects.create(
            customer=customer,
            number=_generate_order_number(),
            status=OrderStatus.PENDENTE,
            total=Decimal('0.00'),
            observations=data.observations or '',
            idempotency_key=data.idempotency_key,
        )

        total = Decimal('0.00')

        for it in data.items:
            p = products_by_id[it.product_id]
            unit_price = Decimal(p.price)
            subtotal = unit_price * Decimal(it.qty)

            p.stock_qty -= it.qty
            p.save(update_fields=['stock_qty', 'updated_at'])

            OrderItem.objects.create(
                order=order,
                product=p,
                qty=it.qty,
                unit_price=unit_price,
                subtotal=subtotal,
            )

            total += subtotal

        order.total = total
        order.save(update_fields=['total', 'updated_at'])

        OrderStatusHistory.objects.create(
            order=order,
            from_status=OrderStatus.PENDENTE,
            to_status=OrderStatus.PENDENTE,
            changed_by=None,
            note='created',
        )

        return order

from django.db import transaction
from apps.orders.domain.transitions import can_transition

@staticmethod
@transaction.atomic
def change_status(order_id: int, new_status: str, user=None, note: str = '') -> Order:
    order = Order.objects.select_for_update().filter(id=order_id).first()
    if not order:
        raise NotFoundError('Pedido não encontrado')

    if not can_transition(order.status, new_status):
        raise ConflictError(f'Transição inválida {order.status} -> {new_status}')

    old_status = order.status
    order.status = new_status
    order.save(update_fields=['status', 'updated_at'])

    OrderStatusHistory.objects.create(
        order=order,
        from_status=old_status,
        to_status=new_status,
        changed_by=user,
        note=note or '',
    )

    return order

@staticmethod
@transaction.atomic
def cancel_order(order_id: int, user=None, note: str = '') -> Order:
    order = Order.objects.select_for_update().filter(id=order_id).first()
    if not order:
        raise NotFoundError('Pedido não encontrado')

    if order.status not in [OrderStatus.PENDENTE, OrderStatus.CONFIRMADO]:
        raise ConflictError('Pedido não pode ser cancelado neste status')

    # devolver estoque
    items = order.items.select_related('product').all()

    for it in items:
        product = Product.objects.select_for_update().get(id=it.product_id)
        product.stock_qty += it.qty
        product.save(update_fields=['stock_qty', 'updated_at'])

    old_status = order.status
    order.status = OrderStatus.CANCELADO
    order.save(update_fields=['status', 'updated_at'])

    OrderStatusHistory.objects.create(
        order=order,
        from_status=old_status,
        to_status=OrderStatus.CANCELADO,
        changed_by=user,
        note=note or 'cancelled',
    )

    return order
