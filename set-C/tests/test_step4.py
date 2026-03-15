"""Step 4: Event system + inventory checks on cart."""
import pytest
from models import Product
from catalog import ProductCatalog
from inventory import InventoryManager
from cart import ShoppingCart
from pricing import PricingEngine
from order import Order, OrderLine, OrderStatus
from order_service import OrderService
from events import EventBus, Event
from exceptions import InsufficientStockError


def _evented_setup():
    bus = EventBus()
    cat = ProductCatalog(event_bus=bus)
    cat.add_product(Product(id="p1", name="Widget", price=100.0, weight=2.0))
    cat.add_product(Product(id="p2", name="Gadget", price=200.0, weight=3.0))
    inv = InventoryManager(event_bus=bus)
    inv.set_stock("p1", 50)
    inv.set_stock("p2", 20)
    return bus, cat, inv


class TestEventBus:
    def test_publish_subscribe(self):
        bus = EventBus()
        received = []
        bus.subscribe("test", lambda e: received.append(e))
        bus.publish("test", {"key": "value"})
        assert len(received) == 1
        assert received[0].data["key"] == "value"

    def test_history(self):
        bus = EventBus()
        bus.publish("a", {})
        bus.publish("b", {})
        assert len(bus.get_history()) == 2

    def test_history_by_type(self):
        bus = EventBus()
        bus.publish("a", {})
        bus.publish("b", {})
        bus.publish("a", {})
        assert len(bus.get_history_by_type("a")) == 2


class TestCatalogEvents:
    def test_product_added_event(self):
        bus, cat, inv = _evented_setup()
        # 2 products already added in setup
        events = bus.get_history_by_type("product_added")
        assert len(events) == 2

    def test_product_removed_event(self):
        bus, cat, inv = _evented_setup()
        cat.remove_product("p1")
        events = bus.get_history_by_type("product_removed")
        assert len(events) == 1
        assert events[0].data["product_id"] == "p1"

    def test_product_updated_event(self):
        bus, cat, inv = _evented_setup()
        cat.update_product("p1", name="New Widget")
        events = bus.get_history_by_type("product_updated")
        assert len(events) == 1


class TestInventoryEvents:
    def test_stock_changed_event(self):
        bus, cat, inv = _evented_setup()
        bus.clear_history()
        inv.set_stock("p1", 999)
        events = bus.get_history_by_type("stock_changed")
        assert len(events) == 1
        assert events[0].data["product_id"] == "p1"
        assert events[0].data["new_stock"] == 999


class TestCartEvents:
    def test_cart_item_added_event(self):
        bus, cat, inv = _evented_setup()
        cart = ShoppingCart(cat, event_bus=bus)
        bus.clear_history()
        cart.add_item("p1", 2)
        events = bus.get_history_by_type("cart_item_added")
        assert len(events) == 1

    def test_cart_item_removed_event(self):
        bus, cat, inv = _evented_setup()
        cart = ShoppingCart(cat, event_bus=bus)
        cart.add_item("p1", 2)
        bus.clear_history()
        cart.remove_item("p1")
        events = bus.get_history_by_type("cart_item_removed")
        assert len(events) == 1


class TestCartInventoryCheck:
    def test_add_checks_inventory(self):
        bus, cat, inv = _evented_setup()
        cart = ShoppingCart(cat, inventory=inv)
        cart.add_item("p1", 50)  # exactly at limit
        with pytest.raises(InsufficientStockError):
            cart.add_item("p2", 21)  # over limit

    def test_add_without_inventory_no_check(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="W", price=10.0))
        cart = ShoppingCart(cat)  # no inventory
        cart.add_item("p1", 999999)  # should work, no check
        assert cart.get_item("p1").quantity == 999999
