import json
import logging

from apps.common.redis import get_redis
from apps.orders.models import Order, OrderDomainEvent

logger = logging.getLogger(__name__)


def publish_order_status_changed(order: Order, from_status: str, to_status: str, note: str = "") -> None:
    payload = {
        "order_id": order.id,
        "number": order.number,
        "from_status": from_status,
        "to_status": to_status,
        "note": note,
    }
    OrderDomainEvent.objects.create(event_type="ORDER_STATUS_CHANGED", order=order, payload=payload)
    try:
        get_redis().publish("domain_events:orders", json.dumps(payload))
    except Exception:
        logger.warning("failed to publish domain event to redis")

    consume_order_status_changed(payload)


def consume_order_status_changed(payload: dict) -> None:
    logger.info("order_status_changed_consumed order=%s from=%s to=%s", payload["order_id"], payload["from_status"], payload["to_status"])
