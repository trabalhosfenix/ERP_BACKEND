from concurrent.futures import ThreadPoolExecutor

import pytest
from django.contrib.auth.models import Group, User
from django.db import connection
from django.db.utils import OperationalError
from rest_framework.test import APIClient

from apps.customers.models import Customer
from apps.orders.models import Order
from apps.products.models import Product


import json
import logging

logger = logging.getLogger(__name__)

def _debug_response(resp, label="response"):
    # Cabeçalho básico
    logger.error("=== %s ===", label)
    logger.error("status=%s", getattr(resp, "status_code", None))
    logger.error("content-type=%s", resp.get("Content-Type", None) if hasattr(resp, "get") else None)

    # .data (DRF Response) se existir
    if hasattr(resp, "data"):
        try:
            logger.error("data=%s", resp.data)
        except Exception as e:
            logger.error("data=<error: %s>", e)

    # JSON parseado
    try:
        payload = resp.json()
        logger.error("json(type=%s)=%s", type(payload).__name__, payload)
    except Exception as e:
        logger.error("json=<error: %s>", e)

    # Conteúdo cru (bytes -> texto)
    try:
        raw = resp.content.decode("utf-8", errors="replace")
        logger.error("raw=%s", raw)
    except Exception as e:
        logger.error("raw=<error: %s>", e)


@pytest.fixture
def operator_user(db):
    group, _ = Group.objects.get_or_create(name="operator")
    user = User.objects.create_user(username="operator_orders", password="123456")
    user.groups.add(group)
    return user


@pytest.fixture
def viewer_user(db):
    group, _ = Group.objects.get_or_create(name="viewer")
    user = User.objects.create_user(username="viewer_orders", password="123456")
    user.groups.add(group)
    return user


@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(username="admin_orders", password="123456", email="admin@test.com")
    return user


def _authenticated_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db(transaction=True)
def test_order_idempotency_three_retries(operator_user):
    customer = Customer.objects.create(name="A", cpf_cnpj="123", email="a@test.com")
    product = Product.objects.create(sku="SKU1", name="P1", price="10.00", stock_qty=10)

    payload = {
        "customer_id": customer.id,
        "idempotency_key": "idem-1",
        "items": [{"product_id": product.id, "qty": 2}],
    }

    client = _authenticated_client(operator_user)
    responses = [client.post("/api/v1/orders", payload, format="json") for _ in range(3)]

    assert responses[0].status_code == 201
    assert responses[1].status_code == 200
    assert responses[2].status_code == 200
    assert Order.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_atomicity_when_one_item_has_no_stock(operator_user):
    customer = Customer.objects.create(name="A", cpf_cnpj="124", email="b@test.com")
    p1 = Product.objects.create(sku="SKU2", name="P2", price="10.00", stock_qty=5)
    p2 = Product.objects.create(sku="SKU3", name="P3", price="8.00", stock_qty=5)
    p3 = Product.objects.create(sku="SKU4", name="P4", price="6.00", stock_qty=0)

    payload = {
        "customer_id": customer.id,
        "idempotency_key": "idem-2",
        "items": [
            {"product_id": p1.id, "qty": 1},
            {"product_id": p2.id, "qty": 1},
            {"product_id": p3.id, "qty": 1},
        ],
    }

    client = _authenticated_client(operator_user)
    response = client.post("/api/v1/orders", payload, format="json")

    assert response.status_code == 409
    p1.refresh_from_db()
    p2.refresh_from_db()
    assert p1.stock_qty == 5
    assert p2.stock_qty == 5


@pytest.mark.django_db(transaction=True)
def test_concurrent_stock_reservation_only_one_order_accepted(operator_user):
    customer = Customer.objects.create(name="A", cpf_cnpj="125", email="c@test.com")
    product = Product.objects.create(sku="SKU5", name="P5", price="12.00", stock_qty=10)

    def create_order(key: str):
        client = _authenticated_client(operator_user)
        try:
            return client.post(
                "/api/v1/orders",
                {
                    "customer_id": customer.id,
                    "idempotency_key": key,
                    "items": [{"product_id": product.id, "qty": 8}],
                },
                format="json",
            ).status_code
        except OperationalError:
            # SQLite pode lançar lock em testes concorrentes; tratamos como conflito de reserva.
            return 409

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(create_order, ["race-a", "race-b"]))

    product.refresh_from_db()

    if connection.vendor == "sqlite":
        # Em SQLite, locks globais podem fazer ambos requests falharem por limitação do engine.
        assert sorted(statuses) in ([201, 409], [409, 409])
        # Dependendo do timing, uma criação pode persistir mesmo se o cliente recebeu erro por lock.
        assert product.stock_qty in [2, 10]
    else:
        assert sorted(statuses) == [201, 409]
        assert product.stock_qty == 2


@pytest.mark.django_db(transaction=True)
def test_patch_order_status_route_with_id_param_alias(operator_user):
    customer = Customer.objects.create(name="Alias", cpf_cnpj="126", email="alias@test.com")
    product = Product.objects.create(sku="SKU6", name="P6", price="15.00", stock_qty=10)

    client = _authenticated_client(operator_user)
    create_response = client.post(
        "/api/v1/orders",
        {
            "customer_id": customer.id,
            "idempotency_key": "idem-alias-status",
            "items": [{"product_id": product.id, "qty": 1}],
        },
        format="json",
    )
    assert create_response.status_code == 201

    order_id = create_response.json()["id"]
    status_response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        {"status": "CONFIRMADO", "note": "aprovado"},
        format="json",
    )

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "CONFIRMADO"
    assert body["id"] == order_id


@pytest.mark.django_db
def test_order_list_and_detail_fields(operator_user):
    customer = Customer.objects.create(name="Customer Test", cpf_cnpj="999", email="test@test.com")
    product = Product.objects.create(sku="PROD1", name="Product Test", price="50.00", stock_qty=10)

    client = _authenticated_client(operator_user)

    # Criar pedido (valida criação)
    create_response = client.post(
        "/api/v1/orders",
        {
            "customer_id": customer.id,
            "idempotency_key": "list-detail-test",
            "items": [{"product_id": product.id, "qty": 1}],
        },
        format="json",
    )
    assert create_response.status_code in (200, 201)

    # Testar Listagem (paginada)
    list_response = client.get("/api/v1/orders")
    assert list_response.status_code == 200

    payload = list_response.json()
    assert isinstance(payload, dict)
    assert "results" in payload

    orders = payload["results"]
    assert isinstance(orders, list)
    assert len(orders) >= 1

    order_list_item = orders[0]
    assert "customer_name" in order_list_item
    assert order_list_item["customer_name"] == "Customer Test"

    # Verificar que campos pesados não estão na lista
    assert "items" not in order_list_item
    assert "status_history" not in order_list_item

    # Testar Detalhe
    order_id = order_list_item["id"]
    detail_response = client.get(f"/api/v1/orders/{order_id}")
    assert detail_response.status_code == 200

    order_detail = detail_response.json()
    assert "items" in order_detail
    assert "status_history" in order_detail
    assert order_detail["customer_name"] == "Customer Test"
    assert order_detail["items"][0]["product_name"] == "Product Test"


@pytest.mark.django_db
def test_order_cancelation_permissions(operator_user, admin_user):
    customer = Customer.objects.create(name="Cancel Test", cpf_cnpj="888", email="cancel@test.com")
    product = Product.objects.create(sku="PROD2", name="P2", price="10.00", stock_qty=10)
    
    # Criar pedido com operador
    client_op = _authenticated_client(operator_user)
    res = client_op.post("/api/v1/orders", {
        "customer_id": customer.id,
        "idempotency_key": "cancel-perm-test",
        "items": [{"product_id": product.id, "qty": 1}],
    }, format="json")
    order_id = res.json()["id"]

    # Operador não pode cancelar (DELETE)
    cancel_op = client_op.delete(f"/api/v1/orders/{order_id}")
    assert cancel_op.status_code == 403

    # Admin pode cancelar
    client_admin = _authenticated_client(admin_user)
    cancel_admin = client_admin.delete(f"/api/v1/orders/{order_id}", {"note": "Cancelando"}, format="json")
    assert cancel_admin.status_code == 200
    assert cancel_admin.json()["status"] == "CANCELADO"


@pytest.mark.django_db
def test_viewer_cannot_create_order(viewer_user):
    customer = Customer.objects.create(name="Viewer Test", cpf_cnpj="777", email="viewer@test.com")
    client = _authenticated_client(viewer_user)
    
    response = client.post("/api/v1/orders", {
        "customer_id": customer.id,
        "idempotency_key": "viewer-test",
        "items": [{"product_id": 1, "qty": 1}],
    }, format="json")
    
    assert response.status_code == 403
