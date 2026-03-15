"""Final integration tests — NOT shown to AI during development.

Tests cross-step interactions across all 8 steps.
Each test targets a specific spaghetti pattern from sequential development.
"""
import pytest
from models import Product, ProductStatus, Category
from catalog import ProductCatalog
from inventory import InventoryManager
from cart import ShoppingCart
from pricing import PricingEngine, TaxCalculator
from order import OrderStatus
from order_service import OrderService
from events import EventBus
from discounts import Discount, DiscountType, DiscountEngine
from reviews import Review, ReviewManager
from wishlist import Wishlist
from coupons import Coupon, CouponManager
from reports import ReportGenerator
from serializer import serialize_product, deserialize_product
from exceptions import InsufficientStockError, InvalidProductError


def _e2e_setup():
    """Full system setup with all components wired together."""
    bus = EventBus()
    rm = ReviewManager(event_bus=bus)
    cat = ProductCatalog(event_bus=bus, review_manager=rm)
    cat.add_category(Category(id="c1", name="Electronics"))
    cat.add_category(Category(id="c2", name="Accessories"))
    cat.add_product(Product(id="p1", name="Premium Widget", price=100.0,
                            weight=2.0, category_id="c1"))
    cat.add_product(Product(id="p2", name="Basic Gadget", price=50.0,
                            weight=1.0, category_id="c2"))
    cat.add_product(Product(id="p3", name="Super Widget Pro", price=300.0,
                            weight=5.0, category_id="c1"))
    inv = InventoryManager(event_bus=bus)
    inv.set_stock("p1", 100)
    inv.set_stock("p2", 200)
    inv.set_stock("p3", 50)
    de = DiscountEngine()
    cm = CouponManager()
    pe = PricingEngine(TaxCalculator(rate=0.1), discount_engine=de, coupon_manager=cm)
    return bus, cat, inv, de, cm, pe, rm


# --- E2E Full Pipeline ---

class TestEndToEndPipeline:
    def test_full_flow_with_discount_reservation_and_refund(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        de.add_discount(Discount(id="d1", name="10% off electronics",
                                 discount_type=DiscountType.PERCENTAGE, value=0.1,
                                 applicable_category_ids=["c1"]))
        cart = ShoppingCart(cat, inventory=inv, event_bus=bus)
        cart.add_item("p1", 2)   # 100*2=200, 10% off → 180
        cart.add_item("p2", 3)   # 50*3=150, no cat discount
        # Subtotal with discount
        assert pe.calculate_subtotal(cart) == 330.0, (
            "p1 (c1) should get 10% discount: 200→180, p2 stays 150, total 330"
        )
        svc = OrderService(cat, inv, pe, event_bus=bus)
        order = svc.create_order(cart)
        assert cart.is_empty()
        # Deliver then refund
        order.transition_to(OrderStatus.CONFIRMED)
        order.transition_to(OrderStatus.SHIPPED)
        order.transition_to(OrderStatus.DELIVERED)
        svc.refund_order(order)
        assert order.status == OrderStatus.REFUNDED
        assert inv.get_stock("p1") == 100  # restored


# --- Case Sensitivity ---

class TestCaseSensitivity:
    def test_catalog_search(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        assert len(cat.search("widget")) == 2
        assert len(cat.search("GADGET")) == 1

    def test_filter_by_status_after_all_steps(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        assert len(cat.filter_by_status(ProductStatus.ACTIVE)) == 3


# --- Defensive Copies ---

class TestDefensiveCopies:
    def test_list_products_copy(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cat.list_products().clear()
        assert cat.count() == 3

    def test_inventory_stock_copy(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        inv.get_all_stock().clear()
        assert inv.get_stock("p1") == 100

    def test_cart_items_copy(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cart = ShoppingCart(cat)
        cart.add_item("p1", 2)
        cart.get_items().clear()
        assert cart.get_item("p1") is not None

    def test_wishlist_items_copy(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        wl = Wishlist(user_id="u1")
        wl.add_item("p1")
        wl.get_items().clear()
        assert wl.count() == 1

    def test_order_list_copy(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cart = ShoppingCart(cat)
        cart.add_item("p1", 1)
        svc = OrderService(cat, inv, pe)
        svc.create_order(cart)
        svc.get_all_orders().clear()
        assert len(svc.get_all_orders()) == 1


# --- Events Everywhere ---

class TestEventsCrossCutting:
    def test_adjust_stock_emits_event(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        bus.clear_history()
        inv.adjust_stock("p1", -10)
        assert len(bus.get_history_by_type("stock_changed")) >= 1

    def test_catalog_update_emits_event(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        bus.clear_history()
        cat.update_product("p1", price=150.0)
        assert len(bus.get_history_by_type("product_updated")) >= 1

    def test_order_cancel_emits_event(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cart = ShoppingCart(cat, inventory=inv, event_bus=bus)
        cart.add_item("p1", 2)
        svc = OrderService(cat, inv, pe, event_bus=bus)
        order = svc.create_order(cart)
        bus.clear_history()
        svc.cancel_order(order)
        assert len(bus.get_history_by_type("order_status_changed")) >= 1

    def test_refund_emits_event(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cart = ShoppingCart(cat, event_bus=bus)
        cart.add_item("p1", 1)
        svc = OrderService(cat, inv, pe, event_bus=bus)
        order = svc.create_order(cart)
        order.transition_to(OrderStatus.CONFIRMED)
        order.transition_to(OrderStatus.SHIPPED)
        order.transition_to(OrderStatus.DELIVERED)
        bus.clear_history()
        svc.refund_order(order)
        assert len(bus.get_history_by_type("order_refunded")) >= 1

    def test_review_emits_event(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        bus.clear_history()
        rm.add_review(Review(id="r1", product_id="p1", user_id="u1", rating=5))
        assert len(bus.get_history_by_type("review_added")) >= 1


# --- Reservation Consistency ---

class TestReservationConsistency:
    def test_cart_clear_releases_reservations(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cart = ShoppingCart(cat, inventory=inv)
        cart.add_item("p1", 10)
        cart.add_item("p2", 5)
        cart.clear()
        assert inv.get_available_stock("p1") == 100
        assert inv.get_available_stock("p2") == 200

    def test_cart_update_quantity_adjusts_reservation(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cart = ShoppingCart(cat, inventory=inv)
        cart.add_item("p1", 10)
        cart.update_quantity("p1", 3)
        assert inv.get_available_stock("p1") == 97

    def test_order_confirms_reservations(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cart = ShoppingCart(cat, inventory=inv)
        cart.add_item("p1", 10)
        assert inv.get_stock("p1") == 100
        assert inv.get_available_stock("p1") == 90
        svc = OrderService(cat, inv, pe)
        svc.create_order(cart)
        assert inv.get_stock("p1") == 90
        assert inv.get_available_stock("p1") == 90


# --- Serializer Backward Compatibility ---

class TestSerializerCompat:
    def test_weight_serialized(self):
        p = Product(id="x1", name="Test", price=10.0, weight=2.5, tags=["sale"])
        d = serialize_product(p)
        p2 = deserialize_product(d)
        assert p2.weight == 2.5

    def test_category_serialized(self):
        p = Product(id="x1", name="Test", price=10.0, category_id="c1")
        d = serialize_product(p)
        p2 = deserialize_product(d)
        assert p2.category_id == "c1"


# --- Validation Cross-Step ---

class TestValidationIntegration:
    def test_validation_doesnt_break_step1_tests(self):
        """Basic product with valid data should still work."""
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="Widget", price=10.0))
        assert cat.count() == 1

    def test_update_with_empty_name_rejected(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="Widget", price=10.0))
        with pytest.raises(InvalidProductError):
            cat.update_product("p1", name="")


# --- Report with Full Data ---

class TestReportsIntegration:
    def test_inventory_report_with_reservations(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cart = ShoppingCart(cat, inventory=inv)
        cart.add_item("p1", 95)  # reserve 95 of 100
        rg = ReportGenerator(cat, inv)
        report = rg.inventory_report()
        assert report["total_stock"] == 350  # 100+200+50
        assert "p1" not in report["low_stock_items"]  # total is 100, not low

    def test_top_rated_with_reviews(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        rm.add_review(Review(id="r1", product_id="p1", user_id="u1", rating=5))
        rm.add_review(Review(id="r2", product_id="p2", user_id="u1", rating=2))
        rm.add_review(Review(id="r3", product_id="p3", user_id="u1", rating=4))
        rg = ReportGenerator(cat, inv, review_manager=rm)
        top = rg.top_rated_products(n=2)
        assert len(top) == 2
        assert top[0].id == "p1"  # rating 5

    def test_statistics_includes_rating(self):
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        rm.add_review(Review(id="r1", product_id="p1", user_id="u1", rating=4))
        stats = cat.get_statistics()
        assert "average_rating" in stats


# --- Backward Compatibility ---

class TestBackwardCompat:
    def test_basic_product_no_extras(self):
        cat = ProductCatalog()
        p = Product(id="x1", name="Simple", price=5.0)
        cat.add_product(p)
        assert cat.get_product("x1").name == "Simple"

    def test_basic_inventory(self):
        inv = InventoryManager()
        inv.set_stock("x1", 50)
        inv.adjust_stock("x1", -20)
        assert inv.get_stock("x1") == 30

    def test_cart_without_inventory(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="W", price=10.0))
        cart = ShoppingCart(cat)
        cart.add_item("p1", 999)
        assert cart.get_item("p1").quantity == 999


# --- Expanded Defensive Copies ---

class TestDefensiveCopiesExpanded:
    def test_product_to_dict_deep_copy(self):
        """Mutating to_dict() result must not affect the product."""
        p = Product(id="p1", name="Widget", price=10.0, tags=["sale"], metadata={"color": "red"})
        d = p.to_dict()
        d["tags"].append("MUTATED")
        d["metadata"]["injected"] = True
        assert "MUTATED" not in p.tags
        assert "injected" not in p.metadata

    def test_order_to_dict_deep_copy(self):
        """Mutating order.to_dict() result must not affect the order."""
        from order import Order, OrderLine
        line = OrderLine("p1", "Widget", 10.0, 2, 1.0)
        order = Order(id="o1", lines=[line])
        d = order.to_dict()
        d["lines"].clear()
        assert len(order.lines) == 1

    def test_event_history_copy(self):
        """Mutating get_history() must not affect EventBus internal state."""
        bus = EventBus()
        bus.publish("test_event", {"key": "val"})
        history = bus.get_history()
        history.clear()
        assert len(bus.get_history()) == 1


# --- Expanded Reservation Consistency ---

class TestReservationConsistencyExpanded:
    def test_update_quantity_releases_old_and_creates_new_reservation(self):
        """update_quantity must release old reservation before creating new."""
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cart = ShoppingCart(cat, inventory=inv)
        cart.add_item("p1", 10)
        assert inv.get_available_stock("p1") == 90
        cart.update_quantity("p1", 5)
        assert inv.get_available_stock("p1") == 95
        cart.update_quantity("p1", 20)
        assert inv.get_available_stock("p1") == 80

    def test_order_creates_without_inventory_uses_adjust_stock(self):
        """Cart without inventory: order creation uses adjust_stock directly."""
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cart = ShoppingCart(cat)  # no inventory
        cart.add_item("p1", 5)
        svc = OrderService(cat, inv, pe)
        svc.create_order(cart)
        assert inv.get_stock("p1") == 95

    def test_clear_releases_all_reservations_and_restores_stock(self):
        """After cart.clear(), available stock must fully restore."""
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cart = ShoppingCart(cat, inventory=inv)
        cart.add_item("p1", 30)
        cart.add_item("p2", 50)
        cart.add_item("p3", 10)
        assert inv.get_available_stock("p1") == 70
        assert inv.get_available_stock("p2") == 150
        assert inv.get_available_stock("p3") == 40
        cart.clear()
        assert inv.get_available_stock("p1") == 100
        assert inv.get_available_stock("p2") == 200
        assert inv.get_available_stock("p3") == 50

    def test_remove_item_releases_reservation(self):
        """Removing item from cart must release its reservation."""
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cart = ShoppingCart(cat, inventory=inv)
        cart.add_item("p1", 10)
        assert inv.get_available_stock("p1") == 90
        cart.remove_item("p1")
        assert inv.get_available_stock("p1") == 100


# --- Expanded Events Cross-Cutting ---

class TestEventsCrossCuttingExpanded:
    def test_all_catalog_mutations_emit_events(self):
        """catalog add/remove/update must all emit events."""
        bus = EventBus()
        cat = ProductCatalog(event_bus=bus)
        cat.add_product(Product(id="p1", name="Widget", price=10.0))
        cat.update_product("p1", price=20.0)
        cat.remove_product("p1")
        assert len(bus.get_history_by_type("product_added")) == 1
        assert len(bus.get_history_by_type("product_updated")) == 1
        assert len(bus.get_history_by_type("product_removed")) == 1

    def test_inventory_set_and_adjust_emit_events(self):
        """Both set_stock and adjust_stock must emit stock_changed."""
        bus = EventBus()
        inv = InventoryManager(event_bus=bus)
        inv.set_stock("p1", 50)
        inv.adjust_stock("p1", -10)
        events = bus.get_history_by_type("stock_changed")
        assert len(events) == 2
        assert events[0].data["new_stock"] == 50
        assert events[1].data["new_stock"] == 40

    def test_cart_add_remove_emit_events(self):
        """Cart add and remove must emit events."""
        bus = EventBus()
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="W", price=10.0))
        cart = ShoppingCart(cat, event_bus=bus)
        cart.add_item("p1", 2)
        cart.remove_item("p1")
        assert len(bus.get_history_by_type("cart_item_added")) == 1
        assert len(bus.get_history_by_type("cart_item_removed")) == 1

    def test_full_workflow_event_history_completeness(self):
        """A full workflow must produce a complete event history."""
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        bus.clear_history()
        cat.add_product(Product(id="p10", name="New Product", price=25.0, weight=1.0))
        inv.set_stock("p10", 50)
        cart = ShoppingCart(cat, inventory=inv, event_bus=bus)
        cart.add_item("p10", 2)
        svc = OrderService(cat, inv, pe, event_bus=bus)
        order = svc.create_order(cart)
        svc.cancel_order(order)
        history = bus.get_history()
        event_types = [e.type for e in history]
        assert "product_added" in event_types
        assert "stock_changed" in event_types
        assert "cart_item_added" in event_types
        assert "order_created" in event_types
        assert "order_status_changed" in event_types

    def test_event_data_contains_expected_fields(self):
        """Event data must contain required fields."""
        bus = EventBus()
        cat = ProductCatalog(event_bus=bus)
        cat.add_product(Product(id="p1", name="W", price=10.0))
        event = bus.get_history_by_type("product_added")[0]
        assert "product_id" in event.data
        assert event.data["product_id"] == "p1"


# --- Expanded Case Sensitivity ---

class TestCaseSensitivityExpanded:
    def test_case_insensitive_search_mixed_case(self):
        """Search must be case-insensitive with mixed case queries."""
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        assert len(cat.search("WiDgEt")) == 2
        assert len(cat.search("premium")) == 1
        assert len(cat.search("BASIC")) == 1

    def test_case_insensitive_tag_matching(self):
        """Tag filtering must be case-insensitive."""
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="W1", price=10.0, tags=["SALE", "Featured"]))
        cat.add_product(Product(id="p2", name="W2", price=20.0, tags=["sale", "clearance"]))
        cat.add_product(Product(id="p3", name="W3", price=30.0, tags=["NEW"]))
        results = cat.filter_by_tag("sale")
        assert len(results) == 2
        results_upper = cat.filter_by_tag("FEATURED")
        assert len(results_upper) == 1


# --- Discount + Reservation Interaction ---

class TestDiscountReservationInteraction:
    def test_discount_applied_with_reservation_cart(self):
        """Discounts must apply correctly when cart uses reservation-based inventory."""
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        de.add_discount(Discount(id="d1", name="20% off",
                                 discount_type=DiscountType.PERCENTAGE, value=0.2))
        cart = ShoppingCart(cat, inventory=inv, event_bus=bus)
        cart.add_item("p1", 2)  # 100*2=200, 20% off → 160
        subtotal = pe.calculate_subtotal(cart)
        assert subtotal == 160.0

    def test_price_breakdown_includes_discount_with_reservations(self):
        """Price breakdown must include discount field even with reservation cart."""
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        de.add_discount(Discount(id="d1", name="10% off",
                                 discount_type=DiscountType.PERCENTAGE, value=0.1))
        cart = ShoppingCart(cat, inventory=inv)
        cart.add_item("p1", 1)  # 100, 10% off → 90
        breakdown = pe.get_price_breakdown(cart)
        assert "discount" in breakdown
        assert breakdown["discount"] == 10.0
        assert breakdown["subtotal"] == 90.0


# --- Coupon + Order + Refund Flow ---

class TestCouponOrderRefundFlow:
    def test_full_coupon_order_partial_refund_flow(self):
        """Full flow: apply coupon -> create order -> partial refund -> check amounts."""
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cm.add_coupon(Coupon(code="SAVE10", discount_type=DiscountType.FIXED_AMOUNT,
                             value=10.0, usage_limit=5))
        cart = ShoppingCart(cat, inventory=inv, event_bus=bus)
        cart.add_item("p1", 1)  # price=100
        # Check coupon applies
        breakdown = pe.get_price_breakdown(cart, coupon_code="SAVE10")
        assert "coupon_discount" in breakdown
        assert breakdown["coupon_discount"] == 10.0
        # Create order
        svc = OrderService(cat, inv, pe, event_bus=bus)
        order = svc.create_order(cart)
        # Progress to delivered
        order.transition_to(OrderStatus.CONFIRMED)
        order.transition_to(OrderStatus.SHIPPED)
        order.transition_to(OrderStatus.DELIVERED)
        # Partial refund
        svc.refund_order(order, amount=50.0)
        assert order.refund_amount == 50.0
        assert order.status == OrderStatus.REFUNDED

    def test_coupon_usage_count_maintained_after_use(self):
        """After applying coupon, usage count must increase."""
        bus, cat, inv, de, cm, pe, rm = _e2e_setup()
        cm.add_coupon(Coupon(code="ONCE", discount_type=DiscountType.PERCENTAGE,
                             value=0.1, usage_limit=2))
        coupon = cm.get_coupon("ONCE")
        assert coupon.used_count == 0
        cart = ShoppingCart(cat)
        cart.add_item("p1", 1)
        pe.apply_coupon(cart, "ONCE")
        coupon = cm.get_coupon("ONCE")
        assert coupon.used_count == 1
        # Can use again (limit=2)
        assert coupon.is_valid()


# --- Validation Retroactive ---

class TestValidationRetroactive:
    def test_update_product_validates_negative_price(self):
        """update_product must reject negative price."""
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="Widget", price=10.0))
        with pytest.raises(InvalidProductError):
            cat.update_product("p1", price=-5.0)

    def test_update_product_validates_negative_weight(self):
        """update_product must reject negative weight."""
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="Widget", price=10.0, weight=1.0))
        with pytest.raises(InvalidProductError):
            cat.update_product("p1", weight=-1.0)

    def test_add_product_validates_empty_name(self):
        """add_product must reject empty name."""
        cat = ProductCatalog()
        with pytest.raises(InvalidProductError):
            cat.add_product(Product(id="p1", name="", price=10.0))

    def test_add_product_validates_whitespace_only_name(self):
        """add_product must reject whitespace-only name."""
        cat = ProductCatalog()
        with pytest.raises(InvalidProductError):
            cat.add_product(Product(id="p1", name="   ", price=10.0))

    def test_add_product_validates_negative_price(self):
        """add_product must reject negative price."""
        cat = ProductCatalog()
        with pytest.raises(InvalidProductError):
            cat.add_product(Product(id="p1", name="Widget", price=-10.0))

    def test_update_product_validates_empty_name(self):
        """update_product must also reject empty name."""
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="Widget", price=10.0))
        with pytest.raises(InvalidProductError):
            cat.update_product("p1", name="  ")


# --- Serializer Backward Compatibility Expanded ---

class TestSerializerBackwardCompatExpanded:
    def test_product_without_weight_deserializes(self):
        """Serializer must handle products without weight field (pre-step3)."""
        data = {
            "id": "x1",
            "name": "OldProduct",
            "price": 15.0,
            "description": "",
            "cost": 0.0,
            "category_id": None,
            "status": "ACTIVE",
            "tags": [],
            "created_at": 1000.0,
            "updated_at": 1000.0,
            "metadata": {},
        }
        p = deserialize_product(data)
        assert p.id == "x1"
        assert p.weight == 0.0  # default

    def test_product_with_all_step8_fields(self):
        """Serializer must handle products with all fields including weight."""
        p = Product(id="x1", name="Full", price=99.0, weight=3.5,
                    cost=50.0, category_id="c1", tags=["premium"],
                    metadata={"brand": "ACME"}, description="A full product")
        d = serialize_product(p)
        p2 = deserialize_product(d)
        assert p2.weight == 3.5
        assert p2.cost == 50.0
        assert p2.category_id == "c1"
        assert p2.tags == ["premium"]
        assert p2.metadata == {"brand": "ACME"}
        assert p2.description == "A full product"

    def test_round_trip_preserves_all_fields(self):
        """Serialize then deserialize must preserve all fields exactly."""
        p = Product(id="rt1", name="RoundTrip", price=42.0, weight=1.5,
                    cost=20.0, category_id="c2",
                    status=ProductStatus.INACTIVE,
                    tags=["test", "round-trip"],
                    metadata={"key": "value"})
        d = serialize_product(p)
        p2 = deserialize_product(d)
        assert p2.id == p.id
        assert p2.name == p.name
        assert p2.price == p.price
        assert p2.weight == p.weight
        assert p2.cost == p.cost
        assert p2.category_id == p.category_id
        assert p2.status == p.status
        assert p2.tags == p.tags
        assert p2.metadata == p.metadata
        assert p2.created_at == p.created_at


class TestEventDataImmutability:
    """Event data should be independent from original dict."""

    def test_event_data_not_affected_by_external_mutation(self):
        bus = EventBus()
        data = {"product_id": "p1", "quantity": 10}
        bus.publish("test_event", data)
        data["quantity"] = 999
        data["injected"] = True
        event = bus.get_history()[0]
        assert event.data["quantity"] == 10
        assert "injected" not in event.data

    def test_event_data_mutation_does_not_affect_bus(self):
        bus = EventBus()
        bus.publish("test", {"items": [1, 2, 3]})
        event = bus.get_history()[0]
        event.data["items"].append(4)
        fresh = bus.get_history()[0]
        assert len(fresh.data["items"]) == 3


class TestRefundValidation:
    """Refund amounts must be validated."""

    def _setup_delivered_order(self):
        from models import Product, Category
        from catalog import ProductCatalog
        from inventory import InventoryManager
        from cart import ShoppingCart
        from pricing import PricingEngine, TaxCalculator
        from order_service import OrderService
        from order import OrderStatus

        cat = ProductCatalog()
        cat.add_category(Category(id="c1", name="Cat"))
        cat.add_product(Product(id="p1", name="Widget", price=100.0, category_id="c1"))
        inv = InventoryManager()
        inv.set_stock("p1", 50)
        pe = PricingEngine(TaxCalculator())
        cart = ShoppingCart(cat, inventory=inv)
        cart.add_item("p1", 2)
        svc = OrderService(cat, inv, pe)
        order = svc.create_order(cart)
        order.transition_to(OrderStatus.CONFIRMED)
        order.transition_to(OrderStatus.SHIPPED)
        order.transition_to(OrderStatus.DELIVERED)
        return svc, order

    def test_refund_exceeding_total_raises(self):
        svc, order = self._setup_delivered_order()
        total = order.get_total()
        with pytest.raises(ValueError):
            svc.refund_order(order, amount=total + 100)

    def test_negative_refund_raises(self):
        svc, order = self._setup_delivered_order()
        with pytest.raises(ValueError):
            svc.refund_order(order, amount=-10.0)

    def test_zero_refund_raises(self):
        svc, order = self._setup_delivered_order()
        with pytest.raises(ValueError):
            svc.refund_order(order, amount=0)

    def test_valid_partial_refund_succeeds(self):
        svc, order = self._setup_delivered_order()
        total = order.get_total()
        svc.refund_order(order, amount=total / 2)
        assert order.refund_amount == total / 2


class TestBuyXGetYDiscount:
    """BUY_X_GET_Y discount remainder handling."""

    def _setup(self):
        from models import Product, Category
        from catalog import ProductCatalog
        from inventory import InventoryManager
        from cart import ShoppingCart
        from pricing import PricingEngine, TaxCalculator
        from discounts import Discount, DiscountType, DiscountEngine

        cat = ProductCatalog()
        cat.add_category(Category(id="c1", name="Cat"))
        cat.add_product(Product(id="p1", name="Widget", price=100.0, category_id="c1"))
        inv = InventoryManager()
        inv.set_stock("p1", 100)
        de = DiscountEngine()
        de.add_discount(Discount(id="d1", name="buy 2 get 1",
                                 discount_type=DiscountType.BUY_X_GET_Y,
                                 value=(2, 1)))
        pe = PricingEngine(TaxCalculator(), discount_engine=de)
        cart = ShoppingCart(cat, inventory=inv)
        return cart, pe

    def test_buy2get1_qty5_pays_for_4(self):
        cart, pe = self._setup()
        cart.add_item("p1", 5)
        # 5 items: 1 full group(2+1=3) + 2 remainder = pay for 2+2=4
        assert pe.calculate_subtotal(cart) == 400.0

    def test_buy2get1_qty3_pays_for_2(self):
        cart, pe = self._setup()
        cart.add_item("p1", 3)
        # 3 items: 1 full group(2+1=3) = pay for 2
        assert pe.calculate_subtotal(cart) == 200.0

    def test_buy2get1_qty1_pays_for_1(self):
        cart, pe = self._setup()
        cart.add_item("p1", 1)
        # 1 item: no full group, 1 remainder = pay for 1
        assert pe.calculate_subtotal(cart) == 100.0


class TestReservationEdgeCases:
    """Inventory reservation boundary conditions."""

    def test_reserve_exact_available_stock(self):
        from inventory import InventoryManager
        from exceptions import InsufficientStockError

        inv = InventoryManager()
        inv.set_stock("p1", 100)
        rid1 = inv.reserve("p1", 50)
        assert inv.get_available_stock("p1") == 50
        rid2 = inv.reserve("p1", 50)
        assert inv.get_available_stock("p1") == 0
        with pytest.raises(InsufficientStockError):
            inv.reserve("p1", 1)
        inv.release(rid1)
        assert inv.get_available_stock("p1") == 50

    def test_confirm_then_cancel_order_restores_stock(self):
        from models import Product, Category
        from catalog import ProductCatalog
        from inventory import InventoryManager
        from cart import ShoppingCart
        from pricing import PricingEngine, TaxCalculator
        from order_service import OrderService
        from order import OrderStatus

        cat = ProductCatalog()
        cat.add_category(Category(id="c1", name="Cat"))
        cat.add_product(Product(id="p1", name="W", price=10.0, category_id="c1"))
        inv = InventoryManager()
        inv.set_stock("p1", 100)
        pe = PricingEngine(TaxCalculator())
        cart = ShoppingCart(cat, inventory=inv)
        cart.add_item("p1", 30)
        svc = OrderService(cat, inv, pe)
        order = svc.create_order(cart)
        # After create: stock confirmed (reserved -> deducted)
        assert inv.get_stock("p1") == 70
        # Cancel: should restore
        svc.cancel_order(order)
        assert inv.get_stock("p1") == 100
        assert order.status == OrderStatus.CANCELLED


class TestDiscountBoundary:
    """Discount boundary conditions."""

    def test_min_quantity_not_met(self):
        from discounts import Discount, DiscountType, DiscountEngine

        de = DiscountEngine()
        d = Discount(id="d1", name="bulk", discount_type=DiscountType.PERCENTAGE,
                     value=0.5, min_quantity=5)
        de.add_discount(d)

        # qty=4 below min_quantity=5 -> no discount
        best = de.calculate_best_price(100.0, 4, "c1")
        assert best == 100.0 * 4  # No discount

        # qty=5 at min_quantity -> discount applies
        best = de.calculate_best_price(100.0, 5, "c1")
        assert best == 100.0 * 5 * 0.5  # 50% off

    def test_discount_empty_category_applies_to_all(self):
        from discounts import Discount, DiscountType, DiscountEngine

        de = DiscountEngine()
        d = Discount(id="d1", name="global", discount_type=DiscountType.PERCENTAGE,
                     value=0.5, applicable_category_ids=[])
        de.add_discount(d)

        # Empty list means applies to ALL categories
        best = de.calculate_best_price(100.0, 1, "any_category")
        assert best == 50.0
