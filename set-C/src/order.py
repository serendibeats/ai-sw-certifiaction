import time
from enum import Enum


class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


VALID_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
    OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [OrderStatus.REFUNDED],
    OrderStatus.CANCELLED: [],
    OrderStatus.REFUNDED: [],
}


class OrderLine:
    def __init__(self, product_id, product_name, unit_price, quantity, weight=0.0):
        self.product_id = product_id
        self.product_name = product_name
        self.unit_price = unit_price
        self.quantity = quantity
        self.weight = weight

    def get_subtotal(self):
        return self.unit_price * self.quantity

    def get_total_weight(self):
        return self.weight * self.quantity

    def to_dict(self):
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "unit_price": self.unit_price,
            "quantity": self.quantity,
            "weight": self.weight,
            "subtotal": self.get_subtotal(),
            "total_weight": self.get_total_weight(),
        }


class Order:
    def __init__(self, id, lines, status=OrderStatus.PENDING,
                 shipping_cost=0.0, tax=0.0,
                 created_at=None, updated_at=None,
                 refund_amount=0.0, refunded_at=None):
        self.id = id
        self.lines = lines
        self.status = status
        self.created_at = created_at if created_at is not None else time.time()
        self.updated_at = updated_at if updated_at is not None else time.time()
        self.shipping_cost = shipping_cost
        self.tax = tax
        self.refund_amount = refund_amount
        self.refunded_at = refunded_at

    def transition_to(self, new_status):
        if new_status in VALID_TRANSITIONS.get(self.status, []):
            self.status = new_status
            self.updated_at = time.time()
            return True
        return False

    def get_subtotal(self):
        return sum(line.get_subtotal() for line in self.lines)

    def get_total(self):
        return self.get_subtotal() + self.tax + self.shipping_cost

    def get_total_weight(self):
        return sum(line.get_total_weight() for line in self.lines)

    def to_dict(self):
        return {
            "id": self.id,
            "lines": [line.to_dict() for line in self.lines],
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "shipping_cost": self.shipping_cost,
            "tax": self.tax,
            "subtotal": self.get_subtotal(),
            "total": self.get_total(),
            "total_weight": self.get_total_weight(),
        }
