from concurrent.futures import ThreadPoolExecutor

import pytest
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient

from apps.customers.models import Customer
from apps.orders.models import Order
from apps.products.models import Product


@pytest.mark.django_db(transaction=True)
def test_order_idempotency_three_retries():
    customer = Customer.objects.create(name="A", cpf_cnpj="123", email="a@test.com")
    product = Product.objects.create(sku="SKU1", name="P1", price="10.00", stock_qty=10)

    payload = {
        "customer_id": customer.id,
        "idempotency_key": "idem-1",
        "items": [{"product_id": product.id, "qty": 2}],
    }

    client = APIClient()
    responses = [client.post("/api/v1/orders", payload, format="json") for _ in range(3)]

    assert responses[0].status_code == 201
    assert responses[1].status_code == 200
    assert responses[2].status_code == 200
    assert Order.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_atomicity_when_one_item_has_no_stock():
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

    client = APIClient()
    response = client.post("/api/v1/orders", payload, format="json")

    assert response.status_code == 409
    p1.refresh_from_db()
    p2.refresh_from_db()
    assert p1.stock_qty == 5
    assert p2.stock_qty == 5


@pytest.mark.django_db(transaction=True)
def test_concurrent_stock_reservation_only_one_order_accepted():
    customer = Customer.objects.create(name="A", cpf_cnpj="125", email="c@test.com")
    product = Product.objects.create(sku="SKU5", name="P5", price="12.00", stock_qty=10)

    def create_order(key: str):
        client = APIClient()
        return client.post(
            "/api/v1/orders",
            {
                "customer_id": customer.id,
                "idempotency_key": key,
                "items": [{"product_id": product.id, "qty": 8}],
            },
            format="json",
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(create_order, ["race-a", "race-b"]))

    assert sorted(statuses) == [201, 409]
    product.refresh_from_db()
    assert product.stock_qty == 2


@pytest.mark.django_db(transaction=True)
def test_patch_order_status_route_with_id_param_alias():
    customer = Customer.objects.create(name="Alias", cpf_cnpj="126", email="alias@test.com")
    product = Product.objects.create(sku="SKU6", name="P6", price="15.00", stock_qty=10)

    group, _ = Group.objects.get_or_create(name="operator")
    user = User.objects.create_user(username="operator_patch", password="123456")
    user.groups.add(group)

    client = APIClient()
    client.force_authenticate(user=user)
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
