from exceptions import ProductNotFoundError, InsufficientStockError


class CartItem:
    def __init__(self, product_id, product_name, unit_price, quantity):
        self.product_id = product_id
        self.product_name = product_name
        self.unit_price = unit_price
        self.quantity = quantity

    def get_subtotal(self):
        return self.unit_price * self.quantity

    def to_dict(self):
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "unit_price": self.unit_price,
            "quantity": self.quantity,
            "subtotal": self.get_subtotal(),
        }


class ShoppingCart:
    def __init__(self, catalog, event_bus=None, inventory=None):
        self._catalog = catalog
        self._items = {}
        self._event_bus = event_bus
        self._inventory = inventory
        self._reservations = {}  # {product_id: reservation_id}

    def add_item(self, product_id, quantity=1):
        product = self._catalog.get_product(product_id)  # raises ProductNotFoundError
        if self._inventory:
            # Release existing reservation if any
            if product_id in self._reservations:
                self._inventory.release(self._reservations[product_id])
                del self._reservations[product_id]

            current_in_cart = self._items[product_id].quantity if product_id in self._items else 0
            total_needed = current_in_cart + quantity
            reservation_id = self._inventory.reserve(product_id, total_needed)
            self._reservations[product_id] = reservation_id

        if product_id in self._items:
            self._items[product_id].quantity += quantity
        else:
            self._items[product_id] = CartItem(
                product_id=product_id,
                product_name=product.name,
                unit_price=product.price,
                quantity=quantity,
            )
        if self._event_bus:
            self._event_bus.publish("cart_item_added", {"product_id": product_id, "quantity": quantity})

    def remove_item(self, product_id):
        if product_id not in self._items:
            return False
        del self._items[product_id]
        if self._inventory and product_id in self._reservations:
            self._inventory.release(self._reservations[product_id])
            del self._reservations[product_id]
        if self._event_bus:
            self._event_bus.publish("cart_item_removed", {"product_id": product_id})
        return True

    def update_quantity(self, product_id, quantity):
        if product_id not in self._items:
            raise ProductNotFoundError(product_id)
        if quantity == 0:
            if self._inventory and product_id in self._reservations:
                self._inventory.release(self._reservations[product_id])
                del self._reservations[product_id]
            del self._items[product_id]
        else:
            if self._inventory:
                if product_id in self._reservations:
                    self._inventory.release(self._reservations[product_id])
                    del self._reservations[product_id]
                reservation_id = self._inventory.reserve(product_id, quantity)
                self._reservations[product_id] = reservation_id
            self._items[product_id].quantity = quantity

    def get_item(self, product_id):
        return self._items.get(product_id, None)

    def get_items(self):
        return list(self._items.values())

    def get_subtotal(self):
        return sum(item.get_subtotal() for item in self._items.values())

    def get_item_count(self):
        return sum(item.quantity for item in self._items.values())

    def clear(self):
        if self._inventory:
            for product_id, reservation_id in self._reservations.items():
                self._inventory.release(reservation_id)
            self._reservations.clear()
        self._items.clear()

    def is_empty(self):
        return len(self._items) == 0

    def to_dict(self):
        return {
            "items": [item.to_dict() for item in self._items.values()],
            "subtotal": self.get_subtotal(),
            "item_count": self.get_item_count(),
        }
