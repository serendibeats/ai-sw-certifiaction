"""Step 8: Validation + reports + order tracking."""
import pytest
from models import Product, Category, ProductStatus
from catalog import ProductCatalog
from inventory import InventoryManager
from cart import ShoppingCart
from pricing import PricingEngine, TaxCalculator
from order import OrderStatus
from order_service import OrderService
from reviews import ReviewManager, Review
from reports import ReportGenerator
from exceptions import InvalidProductError


class TestValidation:
    def test_empty_name_raises(self):
        cat = ProductCatalog()
        with pytest.raises(InvalidProductError):
            cat.add_product(Product(id="p1", name="", price=10.0))

    def test_whitespace_name_raises(self):
        cat = ProductCatalog()
        with pytest.raises(InvalidProductError):
            cat.add_product(Product(id="p1", name="   ", price=10.0))

    def test_negative_price_raises(self):
        cat = ProductCatalog()
        with pytest.raises(InvalidProductError):
            cat.add_product(Product(id="p1", name="Widget", price=-5.0))

    def test_negative_weight_raises(self):
        cat = ProductCatalog()
        with pytest.raises(InvalidProductError):
            cat.add_product(Product(id="p1", name="Widget", price=10.0, weight=-1.0))

    def test_update_negative_price_raises(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="Widget", price=10.0))
        with pytest.raises(InvalidProductError):
            cat.update_product("p1", price=-5.0)

    def test_valid_product_passes(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="Widget", price=0.0, weight=0.0))
        assert cat.get_product("p1").name == "Widget"

    def test_category_validation(self):
        cat = ProductCatalog()
        cat.add_category(Category(id="c1", name="Electronics"))
        # Valid category
        cat.add_product(Product(id="p1", name="Phone", price=500.0, category_id="c1"))
        assert cat.count() == 1
        # Invalid category
        with pytest.raises(InvalidProductError):
            cat.add_product(Product(id="p2", name="Book", price=20.0, category_id="nonexistent"))


class TestReports:
    def test_inventory_report(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="A", price=10.0))
        cat.add_product(Product(id="p2", name="B", price=20.0))
        inv = InventoryManager()
        inv.set_stock("p1", 3)
        inv.set_stock("p2", 100)
        rg = ReportGenerator(cat, inv)
        report = rg.inventory_report()
        assert report["total_products"] == 2
        assert report["total_stock"] == 103
        assert "p1" in report["low_stock_items"]

    def test_catalog_report(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="A", price=10.0, category_id="c1"))
        cat.add_product(Product(id="p2", name="B", price=30.0, category_id="c1"))
        cat.add_product(Product(id="p3", name="C", price=20.0, category_id="c2",
                                status=ProductStatus.INACTIVE))
        rg = ReportGenerator(cat, InventoryManager())
        report = rg.catalog_report()
        assert report["by_category"]["c1"] == 2
        assert report["by_status"]["INACTIVE"] == 1
        assert report["price_range"]["min"] == 10.0

    def test_top_rated(self):
        rm = ReviewManager()
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="A", price=10.0))
        cat.add_product(Product(id="p2", name="B", price=20.0))
        rm.add_review(Review(id="r1", product_id="p1", user_id="u1", rating=3))
        rm.add_review(Review(id="r2", product_id="p2", user_id="u1", rating=5))
        rg = ReportGenerator(cat, InventoryManager(), review_manager=rm)
        top = rg.top_rated_products(n=2)
        assert top[0].id == "p2"

    def test_top_rated_no_reviews(self):
        cat = ProductCatalog()
        rg = ReportGenerator(cat, InventoryManager())
        assert rg.top_rated_products() == []


class TestOrderTracking:
    def test_get_order(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="W", price=100.0, weight=1.0))
        inv = InventoryManager()
        inv.set_stock("p1", 50)
        pe = PricingEngine()
        svc = OrderService(cat, inv, pe)
        cart = ShoppingCart(cat)
        cart.add_item("p1", 2)
        order = svc.create_order(cart)
        retrieved = svc.get_order(order.id)
        assert retrieved is not None
        assert retrieved.id == order.id

    def test_get_all_orders(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="W", price=100.0, weight=1.0))
        inv = InventoryManager()
        inv.set_stock("p1", 50)
        pe = PricingEngine()
        svc = OrderService(cat, inv, pe)
        for i in range(3):
            cart = ShoppingCart(cat)
            cart.add_item("p1", 1)
            svc.create_order(cart)
        orders = svc.get_all_orders()
        assert len(orders) == 3

    def test_get_orders_by_status(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="W", price=100.0, weight=1.0))
        inv = InventoryManager()
        inv.set_stock("p1", 50)
        pe = PricingEngine()
        svc = OrderService(cat, inv, pe)
        cart = ShoppingCart(cat)
        cart.add_item("p1", 1)
        order = svc.create_order(cart)
        pending = svc.get_orders_by_status(OrderStatus.PENDING)
        assert len(pending) == 1
