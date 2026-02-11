import pytest

from apps.orders.domain.enums import OrderStatus
from apps.orders.domain.transitions import can_transition
from apps.orders.services.order_service import BusinessError, ConflictError


def test_valid_transitions():
    assert can_transition(OrderStatus.PENDENTE, OrderStatus.CONFIRMADO)
    assert can_transition(OrderStatus.CONFIRMADO, OrderStatus.CANCELADO)


def test_invalid_transitions():
    assert not can_transition(OrderStatus.ENTREGUE, OrderStatus.CANCELADO)
    assert not can_transition(OrderStatus.CANCELADO, OrderStatus.CONFIRMADO)


def test_business_error_codes():
    assert BusinessError.status_code == 400
    assert ConflictError.status_code == 409
