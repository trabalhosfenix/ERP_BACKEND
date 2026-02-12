from .enums import OrderStatus

VALID_TRANSITIONS = {
    OrderStatus.PENDENTE: [OrderStatus.CONFIRMADO, OrderStatus.CANCELADO],
    OrderStatus.CONFIRMADO: [OrderStatus.SEPARADO, OrderStatus.CANCELADO],
    OrderStatus.SEPARADO: [OrderStatus.ENVIADO],
    OrderStatus.ENVIADO: [OrderStatus.ENTREGUE],
    OrderStatus.ENTREGUE: [],
    OrderStatus.CANCELADO: [],
}

def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, [])
