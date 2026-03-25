"""Step 1: Product catalog + inventory foundation."""
import time
import pytest
from models import Product, Category, ProductStatus
from catalog import ProductCatalog
from inventory import InventoryManager
from exceptions import (ProductNotFoundError, DuplicateProductError,
                        InsufficientStockError, CategoryNotFoundError)
from serializer import serialize_product, deserialize_product, serialize_category


class TestModels:
    def test_product_creation(self):
        p = Product(id="p1", name="Widget", price=9.99, cost=5.0)
        assert p.id == "p1" and p.name == "Widget"
        assert p.price == 9.99 and p.cost == 5.0
        assert p.status == ProductStatus.ACTIVE
        assert p.tags == [] and p.metadata == {}

    def test_product_margin(self):
        p = Product(id="p1", name="X", price=100.0, cost=60.0)
        assert p.get_margin() == 40.0

    def test_product_availability(self):
        p = Product(id="p1", name="X", price=10.0, status=ProductStatus.ACTIVE)
        assert p.is_available() is True
        p.status = ProductStatus.DISCONTINUED
        assert p.is_available() is False

    def test_product_update(self):
        p = Product(id="p1", name="X", price=10.0)
        old_updated = p.updated_at
        time.sleep(0.01)
        p.update(name="Y", price=20.0)
        assert p.name == "Y" and p.price == 20.0
        assert p.updated_at > old_updated

    def test_product_to_dict(self):
        p = Product(id="p1", name="X", price=10.0, tags=["sale"])
        d = p.to_dict()
        assert d["id"] == "p1" and d["tags"] == ["sale"]
        assert d["status"] == "ACTIVE"

    def test_category(self):
        c = Category(id="c1", name="Electronics", parent_id=None)
        assert c.id == "c1" and c.name == "Electronics"
        d = c.to_dict()
        assert d["name"] == "Electronics"


class TestCatalog:
    def test_add_get_product(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="Widget", price=10.0))
        p = cat.get_product("p1")
        assert p.name == "Widget"

    def test_duplicate_raises(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="A", price=1.0))
        with pytest.raises(DuplicateProductError):
            cat.add_product(Product(id="p1", name="B", price=2.0))

    def test_remove_product(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="A", price=1.0))
        cat.remove_product("p1")
        with pytest.raises(ProductNotFoundError):
            cat.get_product("p1")

    def test_search(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="Apple Phone", price=999.0))
        cat.add_product(Product(id="p2", name="Apple Watch", price=399.0))
        cat.add_product(Product(id="p3", name="Samsung TV", price=1200.0))
        results = cat.search("Apple")
        assert len(results) == 2

    def test_filter_by_status(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="A", price=1.0, status=ProductStatus.ACTIVE))
        cat.add_product(Product(id="p2", name="B", price=2.0, status=ProductStatus.INACTIVE))
        results = cat.filter_by_status(ProductStatus.ACTIVE)
        assert len(results) == 1

    def test_filter_by_price_range(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="A", price=10.0))
        cat.add_product(Product(id="p2", name="B", price=50.0))
        cat.add_product(Product(id="p3", name="C", price=100.0))
        results = cat.filter_by_price_range(20.0, 80.0)
        assert len(results) == 1

    def test_sort_products(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="Banana", price=3.0))
        cat.add_product(Product(id="p2", name="Apple", price=1.0))
        results = cat.sort_products("name")
        assert results[0].name == "Apple"

    def test_categories(self):
        cat = ProductCatalog()
        cat.add_category(Category(id="c1", name="Electronics"))
        cat.add_category(Category(id="c2", name="Books"))
        cat.add_product(Product(id="p1", name="Phone", price=500.0, category_id="c1"))
        cat.add_product(Product(id="p2", name="Book", price=20.0, category_id="c2"))
        results = cat.get_products_by_category("c1")
        assert len(results) == 1

    def test_statistics(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="A", price=100.0))
        cat.add_product(Product(id="p2", name="B", price=200.0, status=ProductStatus.INACTIVE))
        stats = cat.get_statistics()
        assert stats["total_products"] == 2
        assert stats["active_products"] == 1
        assert stats["average_price"] == 150.0
        assert stats["total_value"] == 300.0


class TestInventory:
    def test_set_get_stock(self):
        inv = InventoryManager()
        inv.set_stock("p1", 100)
        assert inv.get_stock("p1") == 100

    def test_adjust_stock(self):
        inv = InventoryManager()
        inv.set_stock("p1", 100)
        inv.adjust_stock("p1", -30)
        assert inv.get_stock("p1") == 70

    def test_insufficient_stock(self):
        inv = InventoryManager()
        inv.set_stock("p1", 10)
        with pytest.raises(InsufficientStockError):
            inv.adjust_stock("p1", -20)

    def test_low_stock(self):
        inv = InventoryManager()
        inv.set_stock("p1", 3)
        inv.set_stock("p2", 100)
        low = inv.get_low_stock_items(threshold=5)
        assert "p1" in low and "p2" not in low

    def test_availability(self):
        inv = InventoryManager()
        inv.set_stock("p1", 10)
        assert inv.is_available("p1", 10) is True
        assert inv.is_available("p1", 11) is False


class TestSerializer:
    def test_round_trip(self):
        p = Product(id="p1", name="Widget", price=9.99, cost=5.0, tags=["sale"])
        d = serialize_product(p)
        p2 = deserialize_product(d)
        assert p2.id == "p1" and p2.name == "Widget"
        assert p2.price == 9.99 and p2.tags == ["sale"]
