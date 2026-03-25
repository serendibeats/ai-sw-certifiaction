"""Step 5: Discounts + reservations + restructure."""
import pytest
from models import Product
from catalog import ProductCatalog
from inventory import InventoryManager
from cart import ShoppingCart
from pricing import PricingEngine, TaxCalculator
from order_service import OrderService
from discounts import Discount, DiscountType, DiscountEngine
from exceptions import InsufficientStockError


def _full_setup():
    cat = ProductCatalog()
    cat.add_product(Product(id="p1", name="Widget", price=100.0, weight=2.0, category_id="c1"))
    cat.add_product(Product(id="p2", name="Gadget", price=200.0, weight=3.0, category_id="c2"))
    inv = InventoryManager()
    inv.set_stock("p1", 50)
    inv.set_stock("p2", 20)
    return cat, inv


class TestDiscount:
    def test_percentage_discount(self):
        d = Discount(id="d1", name="10% off", discount_type=DiscountType.PERCENTAGE, value=0.1)
        # 100 * 2 = 200, 10% off = 180
        assert d.apply(100.0, 2) == 180.0

    def test_fixed_amount_discount(self):
        d = Discount(id="d1", name="$50 off", discount_type=DiscountType.FIXED_AMOUNT, value=50.0)
        assert d.apply(100.0, 2) == 150.0  # 200 - 50

    def test_min_quantity_check(self):
        d = Discount(id="d1", name="Bulk", discount_type=DiscountType.PERCENTAGE,
                     value=0.2, min_quantity=5)
        assert d.is_applicable(3) is False
        assert d.is_applicable(5) is True

    def test_category_filter(self):
        d = Discount(id="d1", name="Cat", discount_type=DiscountType.PERCENTAGE,
                     value=0.1, applicable_category_ids=["c1"])
        assert d.is_applicable(1, category_id="c1") is True
        assert d.is_applicable(1, category_id="c2") is False
        # Empty category list = all categories
        d2 = Discount(id="d2", name="All", discount_type=DiscountType.PERCENTAGE, value=0.1)
        assert d2.is_applicable(1, category_id="c2") is True


class TestDiscountEngine:
    def test_best_price(self):
        de = DiscountEngine()
        de.add_discount(Discount(id="d1", name="10%", discount_type=DiscountType.PERCENTAGE, value=0.1))
        de.add_discount(Discount(id="d2", name="$30", discount_type=DiscountType.FIXED_AMOUNT, value=30.0))
        # 100*2=200, 10% off=180, $30 off=170 → best is 170
        best = de.calculate_best_price(100.0, 2)
        assert best == 170.0


class TestPricingWithDiscount:
    def test_subtotal_with_discount(self):
        cat, inv = _full_setup()
        de = DiscountEngine()
        de.add_discount(Discount(id="d1", name="10%", discount_type=DiscountType.PERCENTAGE, value=0.1))
        pe = PricingEngine(TaxCalculator(rate=0.1), discount_engine=de)
        cart = ShoppingCart(cat)
        cart.add_item("p1", 2)  # 100*2=200, 10% off=180
        assert pe.calculate_subtotal(cart) == 180.0

    def test_breakdown_includes_discount(self):
        cat, inv = _full_setup()
        de = DiscountEngine()
        de.add_discount(Discount(id="d1", name="10%", discount_type=DiscountType.PERCENTAGE, value=0.1))
        pe = PricingEngine(TaxCalculator(rate=0.1), discount_engine=de)
        cart = ShoppingCart(cat)
        cart.add_item("p1", 2)  # 200 -> 180 after discount
        bd = pe.get_price_breakdown(cart)
        assert bd["discount"] == 20.0
        assert bd["subtotal"] == 180.0


class TestReservation:
    def test_reserve_and_available(self):
        inv = InventoryManager()
        inv.set_stock("p1", 100)
        rid = inv.reserve("p1", 30)
        assert inv.get_available_stock("p1") == 70
        assert inv.get_stock("p1") == 100  # total unchanged

    def test_release_reservation(self):
        inv = InventoryManager()
        inv.set_stock("p1", 100)
        rid = inv.reserve("p1", 30)
        inv.release(rid)
        assert inv.get_available_stock("p1") == 100

    def test_confirm_reservation(self):
        inv = InventoryManager()
        inv.set_stock("p1", 100)
        rid = inv.reserve("p1", 30)
        inv.confirm(rid)
        assert inv.get_stock("p1") == 70
        assert inv.get_available_stock("p1") == 70

    def test_reserve_insufficient(self):
        inv = InventoryManager()
        inv.set_stock("p1", 10)
        with pytest.raises(InsufficientStockError):
            inv.reserve("p1", 20)


class TestCartReservation:
    def test_cart_add_reserves(self):
        cat, inv = _full_setup()
        cart = ShoppingCart(cat, inventory=inv)
        cart.add_item("p1", 10)
        assert inv.get_available_stock("p1") == 40

    def test_cart_remove_releases(self):
        cat, inv = _full_setup()
        cart = ShoppingCart(cat, inventory=inv)
        cart.add_item("p1", 10)
        cart.remove_item("p1")
        assert inv.get_available_stock("p1") == 50
