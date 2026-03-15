from exceptions import ProductNotFoundError


class Wishlist:
    def __init__(self, user_id, catalog=None, event_bus=None):
        self.user_id = user_id
        self._catalog = catalog
        self._event_bus = event_bus
        self._items = []

    def add_item(self, product_id):
        if product_id in self._items:
            return
        if self._catalog:
            self._catalog.get_product(product_id)  # raises ProductNotFoundError
        self._items.append(product_id)
        if self._event_bus:
            self._event_bus.publish("wishlist_item_added", {"product_id": product_id})

    def remove_item(self, product_id):
        if product_id not in self._items:
            return False
        self._items.remove(product_id)
        if self._event_bus:
            self._event_bus.publish("wishlist_item_removed", {"product_id": product_id})
        return True

    def get_items(self):
        return list(self._items)

    def contains(self, product_id):
        return product_id in self._items

    def count(self):
        return len(self._items)

    def move_to_cart(self, product_id, cart):
        if product_id in self._items:
            self._items.remove(product_id)
            cart.add_item(product_id)
