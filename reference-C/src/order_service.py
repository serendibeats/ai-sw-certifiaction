import time
import uuid
from order import Order, OrderLine, OrderStatus


class OrderService:
    def __init__(self, catalog, inventory, pricing_engine, event_bus=None):
        self._catalog = catalog
        self._inventory = inventory
        self._pricing_engine = pricing_engine
        self._event_bus = event_bus
        self._orders = {}

    def create_order(self, cart, shipping_address=None):
        lines = []
        for item in cart.get_items():
            product = self._catalog.get_product(item.product_id)
            line = OrderLine(
                product_id=item.product_id,
                product_name=item.product_name,
                unit_price=item.unit_price,
                quantity=item.quantity,
                weight=product.weight,
            )
            lines.append(line)

        # Confirm reservations from the cart or adjust stock directly
        if hasattr(cart, '_reservations') and cart._reservations:
            for product_id, reservation_id in list(cart._reservations.items()):
                self._inventory.confirm(reservation_id)
            cart._reservations.clear()
        else:
            for line in lines:
                self._inventory.adjust_stock(line.product_id, -line.quantity)

        order = Order(
            id=str(uuid.uuid4()),
            lines=lines,
        )

        # Calculate shipping
        total_weight = order.get_total_weight()
        order.shipping_cost = self._pricing_engine.calculate_shipping(total_weight)

        # Calculate tax
        order.tax = self._pricing_engine.calculate_tax(cart)

        # Clear cart
        cart.clear()

        self._orders[order.id] = order

        if self._event_bus:
            self._event_bus.publish("order_created", {"order_id": order.id})

        return order

    def cancel_order(self, order):
        old_status = order.status
        if order.transition_to(OrderStatus.CANCELLED):
            # Restore confirmed stock
            for line in order.lines:
                self._inventory.adjust_stock(line.product_id, line.quantity)
            if self._event_bus:
                self._event_bus.publish("order_status_changed", {
                    "order_id": order.id,
                    "old_status": old_status.value,
                    "new_status": OrderStatus.CANCELLED.value,
                })
            return True
        return False

    def refund_order(self, order, amount=None):
        if amount is None:
            amount = order.get_total()
        if amount <= 0 or amount > order.get_total():
            raise ValueError(f"Invalid refund amount: {amount}")
        if not order.transition_to(OrderStatus.REFUNDED):
            raise ValueError(f"Cannot refund order in status {order.status.value}")
        order.refund_amount = amount
        order.refunded_at = time.time()
        # Full refund: restore stock
        if amount == order.get_total():
            for line in order.lines:
                self._inventory.adjust_stock(line.product_id, line.quantity)
        if self._event_bus:
            self._event_bus.publish("order_refunded", {
                "order_id": order.id,
                "amount": amount,
            })
        return True

    def get_order(self, order_id):
        return self._orders.get(order_id)

    def get_all_orders(self):
        return list(self._orders.values())

    def get_orders_by_status(self, status):
        return [o for o in self._orders.values() if o.status == status]

    def get_order_summary(self, order):
        return {
            "order_id": order.id,
            "status": order.status.value,
            "item_count": sum(line.quantity for line in order.lines),
            "subtotal": order.get_subtotal(),
            "tax": order.tax,
            "shipping": order.shipping_cost,
            "total": order.get_total(),
        }
