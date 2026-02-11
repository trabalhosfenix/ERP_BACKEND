import threading
from decimal import Decimal

import pytest
from django.db import close_old_connections

from apps.customers.models import Customer
from apps.products.models import Product
from apps.orders.domain.enums import OrderStatus
from apps.orders.models import Order
from apps.orders.services.order_service import (
    OrderService,
    CreateOrderInput,
    CreateOrderItemInput,
    ConflictError,
)

pytestmark = pytest.mark.django_db(transaction=True)


def make_customer() -> Customer:
    return Customer.objects.create(
        name="Cliente Teste",
        cpf_cnpj="12345678900",
        email="cliente@teste.com",
        phone="11999999999",
        address="Rua X",
        is_active=True,
    )


def make_product(stock: int, price: str = "10.50") -> Product:
    return Product.objects.create(
        sku="SKU-TESTE",
        name="Produto Teste",
        description="",
        price=Decimal(price),
        stock_qty=stock,
        is_active=True,
    )


def test_create_order_reserves_stock_and_calculates_total():
    customer = make_customer()
    product = make_product(stock=10, price="10.50")

    order = OrderService.create_order(
        CreateOrderInput(
            customer_id=customer.id,
            idempotency_key="idem-1",
            observations="obs",
            items=[CreateOrderItemInput(product_id=product.id, qty=2)],
        )
    )

    product.refresh_from_db()
    order.refresh_from_db()

    assert order.status == OrderStatus.PENDENTE
    assert order.total == Decimal("21.00")
    assert order.items.count() == 1

    item = order.items.first()
    assert item.qty == 2
    assert item.unit_price == Decimal("10.50")
    assert item.subtotal == Decimal("21.00")

    assert product.stock_qty == 8


def test_idempotency_same_key_returns_same_order_and_does_not_double_debit_stock():
    customer = make_customer()
    product = make_product(stock=10, price="10.00")

    order1 = OrderService.create_order(
        CreateOrderInput(
            customer_id=customer.id,
            idempotency_key="idem-dup",
            observations="",
            items=[CreateOrderItemInput(product_id=product.id, qty=3)],
        )
    )

    order2 = OrderService.create_order(
        CreateOrderInput(
            customer_id=customer.id,
            idempotency_key="idem-dup",
            observations="qualquer coisa",
            items=[CreateOrderItemInput(product_id=product.id, qty=999)],
        )
    )

    product.refresh_from_db()

    assert order1.id == order2.id
    assert Order.objects.count() == 1
    assert product.stock_qty == 7


def test_cancel_order_restores_stock_and_sets_status_cancelled():
    customer = make_customer()
    product = make_product(stock=10, price="5.00")

    order = OrderService.create_order(
        CreateOrderInput(
            customer_id=customer.id,
            idempotency_key="idem-cancel",
            observations="",
            items=[CreateOrderItemInput(product_id=product.id, qty=4)],
        )
    )

    product.refresh_from_db()
    assert product.stock_qty == 6

    order = OrderService.cancel_order(order_id=order.id, user=None, note="cancel test")

    order.refresh_from_db()
    product.refresh_from_db()

    assert order.status == OrderStatus.CANCELADO
    assert product.stock_qty == 10
    assert order.status_history.count() >= 2


def test_concurrency_two_orders_competing_for_same_stock_one_must_fail():
    customer = make_customer()
    product = make_product(stock=10, price="1.00")

    barrier = threading.Barrier(2)
    results = {"ok": 0, "conflict": 0, "other": []}

    def worker(idem_key: str):
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            OrderService.create_order(
                CreateOrderInput(
                    customer_id=customer.id,
                    idempotency_key=idem_key,
                    observations="",
                    items=[CreateOrderItemInput(product_id=product.id, qty=10)],
                )
            )
            results["ok"] += 1
        except ConflictError:
            results["conflict"] += 1
        except Exception as e:
            results["other"].append(repr(e))

    t1 = threading.Thread(target=worker, args=("idem-a",))
    t2 = threading.Thread(target=worker, args=("idem-b",))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    product.refresh_from_db()

    assert results["other"] == []
    assert results["ok"] == 1
    assert results["conflict"] == 1
    assert product.stock_qty == 0
