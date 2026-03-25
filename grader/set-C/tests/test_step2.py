"""Step 2: Shopping cart + pricing."""
import pytest
from models import Product
from catalog import ProductCatalog
from cart import ShoppingCart, CartItem
from pricing import PricingEngine, TaxCalculator
from exceptions import ProductNotFoundError


def _setup():
    cat = ProductCatalog()
    cat.add_product(Product(id="p1", name="Widget", price=100.0))
    cat.add_product(Product(id="p2", name="Gadget", price=200.0))
    cat.add_product(Product(id="p3", name="Doohickey", price=50.0))
    return cat


class TestCart:
    def test_add_item(self):
        cart = ShoppingCart(_setup())
        cart.add_item("p1", 2)
        item = cart.get_item("p1")
        assert item is not None
        assert item.quantity == 2 and item.unit_price == 100.0

    def test_add_existing_increases_quantity(self):
        cart = ShoppingCart(_setup())
        cart.add_item("p1", 2)
        cart.add_item("p1", 3)
        assert cart.get_item("p1").quantity == 5

    def test_add_nonexistent_raises(self):
        cart = ShoppingCart(_setup())
        with pytest.raises(ProductNotFoundError):
            cart.add_item("nonexistent")

    def test_remove_item(self):
        cart = ShoppingCart(_setup())
        cart.add_item("p1")
        assert cart.remove_item("p1") is True
        assert cart.get_item("p1") is None

    def test_update_quantity(self):
        cart = ShoppingCart(_setup())
        cart.add_item("p1", 5)
        cart.update_quantity("p1", 3)
        assert cart.get_item("p1").quantity == 3

    def test_update_to_zero_removes(self):
        cart = ShoppingCart(_setup())
        cart.add_item("p1", 5)
        cart.update_quantity("p1", 0)
        assert cart.get_item("p1") is None

    def test_subtotal(self):
        cart = ShoppingCart(_setup())
        cart.add_item("p1", 2)  # 200
        cart.add_item("p2", 1)  # 200
        assert cart.get_subtotal() == 400.0

    def test_item_count(self):
        cart = ShoppingCart(_setup())
        cart.add_item("p1", 2)
        cart.add_item("p2", 3)
        assert cart.get_item_count() == 5

    def test_clear(self):
        cart = ShoppingCart(_setup())
        cart.add_item("p1")
        cart.clear()
        assert cart.is_empty() is True


class TestPricing:
    def test_tax_calculation(self):
        tc = TaxCalculator(rate=0.1)
        assert tc.calculate(100.0) == 10.0

    def test_total(self):
        cat = _setup()
        cart = ShoppingCart(cat)
        cart.add_item("p1", 2)  # 200
        engine = PricingEngine(TaxCalculator(rate=0.1))
        total = engine.calculate_total(cart)
        assert total == 220.0  # 200 + 20 tax

    def test_breakdown(self):
        cat = _setup()
        cart = ShoppingCart(cat)
        cart.add_item("p1", 1)  # 100
        engine = PricingEngine(TaxCalculator(rate=0.2))
        bd = engine.get_price_breakdown(cart)
        assert bd["subtotal"] == 100.0
        assert bd["tax"] == 20.0
        assert bd["total"] == 120.0
        assert bd["tax_rate"] == 0.2
