import uuid
from exceptions import InsufficientStockError


class InventoryManager:
    def __init__(self, event_bus=None):
        self._stock = {}
        self._event_bus = event_bus
        self._reservations = {}  # {reservation_id: (product_id, quantity)}

    def set_stock(self, product_id, quantity):
        if quantity < 0:
            quantity = 0
        old_stock = self._stock.get(product_id, 0)
        self._stock[product_id] = quantity
        if self._event_bus:
            self._event_bus.publish("stock_changed", {
                "product_id": product_id,
                "old_stock": old_stock,
                "new_stock": quantity,
            })

    def get_stock(self, product_id):
        return self._stock.get(product_id, 0)

    def adjust_stock(self, product_id, delta):
        current = self._stock.get(product_id, 0)
        new_qty = current + delta
        if new_qty < 0:
            raise InsufficientStockError(product_id, abs(delta), current)
        self._stock[product_id] = new_qty
        if self._event_bus:
            self._event_bus.publish("stock_changed", {
                "product_id": product_id,
                "old_stock": current,
                "new_stock": new_qty,
            })

    def is_available(self, product_id, quantity=1):
        return self.get_available_stock(product_id) >= quantity

    def get_low_stock_items(self, threshold=5):
        return [pid for pid, qty in self._stock.items() if qty <= threshold]

    def get_all_stock(self):
        return dict(self._stock)

    def remove_product(self, product_id):
        if product_id in self._stock:
            del self._stock[product_id]

    def get_total_items(self):
        return sum(self._stock.values())

    def reserve(self, product_id, quantity):
        available = self.get_available_stock(product_id)
        if available < quantity:
            raise InsufficientStockError(product_id, quantity, available)
        reservation_id = str(uuid.uuid4())
        self._reservations[reservation_id] = (product_id, quantity)
        return reservation_id

    def release(self, reservation_id):
        if reservation_id in self._reservations:
            del self._reservations[reservation_id]

    def confirm(self, reservation_id):
        if reservation_id in self._reservations:
            product_id, quantity = self._reservations[reservation_id]
            del self._reservations[reservation_id]
            self.adjust_stock(product_id, -quantity)

    def get_available_stock(self, product_id):
        total = self._stock.get(product_id, 0)
        reserved = sum(qty for pid, qty in self._reservations.values() if pid == product_id)
        return total - reserved
