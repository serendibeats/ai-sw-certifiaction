"""Step 3: Orders + system policies (case-insensitive, defensive copies)."""
import pytest
from models import Product, ProductStatus
from catalog import ProductCatalog
from inventory import InventoryManager
from cart import ShoppingCart
from pricing import PricingEngine, TaxCalculator
from order import Order, OrderLine, OrderStatus
from order_service import OrderService


def _full_setup():
    cat = ProductCatalog()
    cat.add_product(Product(id="p1", name="Widget", price=100.0, weight=2.0))
    cat.add_product(Product(id="p2", name="Gadget", price=200.0, weight=5.0))
    inv = InventoryManager()
    inv.set_stock("p1", 50)
    inv.set_stock("p2", 30)
    pe = PricingEngine(TaxCalculator(rate=0.1))
    return cat, inv, pe


class TestOrderModel:
    def test_order_creation(self):
        line = OrderLine(product_id="p1", product_name="W", unit_price=100.0, quantity=2, weight=2.0)
        order = Order(id="o1", lines=[line])
        assert order.status == OrderStatus.PENDING
        assert order.get_subtotal() == 200.0
        assert line.get_total_weight() == 4.0

    def test_valid_transitions(self):
        order = Order(id="o1", lines=[])
        assert order.transition_to(OrderStatus.CONFIRMED) is True
        assert order.transition_to(OrderStatus.SHIPPED) is True
        assert order.transition_to(OrderStatus.DELIVERED) is True

    def test_invalid_transitions(self):
        order = Order(id="o1", lines=[])
        assert order.transition_to(OrderStatus.SHIPPED) is False  # PENDING->SHIPPED invalid
        order.transition_to(OrderStatus.CANCELLED)
        assert order.transition_to(OrderStatus.CONFIRMED) is False  # terminal

    def test_order_total(self):
        line = OrderLine(product_id="p1", product_name="W", unit_price=100.0, quantity=2, weight=2.0)
        order = Order(id="o1", lines=[line], shipping_cost=2.0, tax=20.0)
        assert order.get_total() == 222.0  # 200 + 20 + 2


class TestOrderService:
    def test_create_order(self):
        cat, inv, pe = _full_setup()
        cart = ShoppingCart(cat)
        cart.add_item("p1", 3)
        cart.add_item("p2", 1)
        svc = OrderService(cat, inv, pe)
        order = svc.create_order(cart)
        assert order.status == OrderStatus.PENDING
        assert len(order.lines) == 2
        # Shipping: (3*2.0 + 1*5.0) * 0.5 = 11*0.5 = 5.5
        assert order.shipping_cost == 5.5
        # Cart should be cleared
        assert cart.is_empty()
        # Inventory reduced
        assert inv.get_stock("p1") == 47

    def test_cancel_restores_stock(self):
        cat, inv, pe = _full_setup()
        cart = ShoppingCart(cat)
        cart.add_item("p1", 5)
        svc = OrderService(cat, inv, pe)
        order = svc.create_order(cart)
        assert inv.get_stock("p1") == 45
        svc.cancel_order(order)
        assert inv.get_stock("p1") == 50
        assert order.status == OrderStatus.CANCELLED


class TestShippingCalc:
    def test_pricing_engine_shipping(self):
        pe = PricingEngine()
        assert pe.calculate_shipping(10.0) == 5.0  # 10 * 0.5


class TestSystemPolicies:
    """These test RETROACTIVE policies from Step 3."""

    def test_catalog_search_case_insensitive(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="Apple Phone", price=999.0))
        assert len(cat.search("apple")) == 1
        assert len(cat.search("APPLE")) == 1

    def test_list_products_returns_copy(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="A", price=1.0))
        result = cat.list_products()
        result.clear()
        assert cat.count() == 1

    def test_inventory_get_all_returns_copy(self):
        inv = InventoryManager()
        inv.set_stock("p1", 100)
        d = inv.get_all_stock()
        d.clear()
        assert inv.get_stock("p1") == 100

    def test_product_with_weight(self):
        p = Product(id="p1", name="X", price=10.0, weight=3.5)
        assert p.weight == 3.5

    def test_product_default_weight(self):
        p = Product(id="p1", name="X", price=10.0)
        assert p.weight == 0.0
