"""Step 7: Coupons + order refunds."""
import pytest
from models import Product
from catalog import ProductCatalog
from inventory import InventoryManager
from cart import ShoppingCart
from pricing import PricingEngine, TaxCalculator
from order import OrderStatus
from order_service import OrderService
from coupons import Coupon, CouponManager
from discounts import DiscountType
from events import EventBus


def _order_setup():
    cat = ProductCatalog()
    cat.add_product(Product(id="p1", name="Widget", price=100.0, weight=2.0))
    cat.add_product(Product(id="p2", name="Gadget", price=50.0, weight=1.0))
    inv = InventoryManager()
    inv.set_stock("p1", 50)
    inv.set_stock("p2", 100)
    pe = PricingEngine(TaxCalculator(rate=0.1))
    return cat, inv, pe


class TestCoupons:
    def test_create_and_validate(self):
        cm = CouponManager()
        cm.add_coupon(Coupon(code="SAVE10", discount_type=DiscountType.PERCENTAGE, value=0.1))
        assert cm.validate_coupon("SAVE10") is True

    def test_apply_percentage(self):
        cm = CouponManager()
        cm.add_coupon(Coupon(code="SAVE10", discount_type=DiscountType.PERCENTAGE, value=0.1))
        result = cm.apply_coupon("SAVE10", 200.0)
        assert result == 180.0

    def test_apply_fixed(self):
        cm = CouponManager()
        cm.add_coupon(Coupon(code="OFF50", discount_type=DiscountType.FIXED_AMOUNT, value=50.0))
        result = cm.apply_coupon("OFF50", 200.0)
        assert result == 150.0

    def test_single_use(self):
        cm = CouponManager()
        cm.add_coupon(Coupon(code="ONCE", discount_type=DiscountType.PERCENTAGE, value=0.1, usage_limit=1))
        cm.apply_coupon("ONCE", 100.0)
        assert cm.validate_coupon("ONCE") is False

    def test_unlimited_use(self):
        cm = CouponManager()
        cm.add_coupon(Coupon(code="ALWAYS", discount_type=DiscountType.PERCENTAGE, value=0.05, usage_limit=0))
        cm.apply_coupon("ALWAYS", 100.0)
        cm.apply_coupon("ALWAYS", 100.0)
        assert cm.validate_coupon("ALWAYS") is True

    def test_invalid_coupon_raises(self):
        cm = CouponManager()
        with pytest.raises(ValueError):
            cm.apply_coupon("NONEXISTENT", 100.0)

    def test_duplicate_code_raises(self):
        cm = CouponManager()
        cm.add_coupon(Coupon(code="X", discount_type=DiscountType.PERCENTAGE, value=0.1))
        with pytest.raises(ValueError):
            cm.add_coupon(Coupon(code="X", discount_type=DiscountType.PERCENTAGE, value=0.2))


class TestRefund:
    def test_full_refund(self):
        cat, inv, pe = _order_setup()
        cart = ShoppingCart(cat)
        cart.add_item("p1", 5)
        svc = OrderService(cat, inv, pe)
        order = svc.create_order(cart)
        assert inv.get_stock("p1") == 45
        order.transition_to(OrderStatus.CONFIRMED)
        order.transition_to(OrderStatus.SHIPPED)
        order.transition_to(OrderStatus.DELIVERED)
        svc.refund_order(order)
        assert order.status == OrderStatus.REFUNDED
        assert inv.get_stock("p1") == 50

    def test_partial_refund(self):
        cat, inv, pe = _order_setup()
        cart = ShoppingCart(cat)
        cart.add_item("p1", 2)
        svc = OrderService(cat, inv, pe)
        order = svc.create_order(cart)
        order.transition_to(OrderStatus.CONFIRMED)
        order.transition_to(OrderStatus.SHIPPED)
        order.transition_to(OrderStatus.DELIVERED)
        svc.refund_order(order, amount=50.0)
        assert order.refund_amount == 50.0
        assert order.status == OrderStatus.REFUNDED

    def test_refund_event(self):
        bus = EventBus()
        cat, inv, pe = _order_setup()
        cart = ShoppingCart(cat)
        cart.add_item("p1", 2)
        svc = OrderService(cat, inv, pe, event_bus=bus)
        order = svc.create_order(cart)
        order.transition_to(OrderStatus.CONFIRMED)
        order.transition_to(OrderStatus.SHIPPED)
        order.transition_to(OrderStatus.DELIVERED)
        bus.clear_history()
        svc.refund_order(order)
        events = bus.get_history_by_type("order_refunded")
        assert len(events) == 1

    def test_refund_pending_raises(self):
        cat, inv, pe = _order_setup()
        cart = ShoppingCart(cat)
        cart.add_item("p1", 1)
        svc = OrderService(cat, inv, pe)
        order = svc.create_order(cart)
        # Order is PENDING, not DELIVERED — can't refund
        with pytest.raises(ValueError):
            svc.refund_order(order)

    def test_refund_after_delivery(self):
        cat, inv, pe = _order_setup()
        cart = ShoppingCart(cat)
        cart.add_item("p1", 3)
        svc = OrderService(cat, inv, pe)
        order = svc.create_order(cart)
        order.transition_to(OrderStatus.CONFIRMED)
        order.transition_to(OrderStatus.SHIPPED)
        order.transition_to(OrderStatus.DELIVERED)
        svc.refund_order(order)
        assert order.status == OrderStatus.REFUNDED
