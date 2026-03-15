class TaxCalculator:
    def __init__(self, rate=0.1):
        self._rate = rate

    def calculate(self, amount):
        return amount * self._rate

    def get_rate(self):
        return self._rate


class PricingEngine:
    def __init__(self, tax_calculator=None, discount_engine=None, coupon_manager=None):
        self._tax_calculator = tax_calculator or TaxCalculator()
        self._discount_engine = discount_engine
        self._coupon_manager = coupon_manager

    def calculate_subtotal(self, cart):
        if self._discount_engine:
            total = 0
            for item in cart.get_items():
                category_id = None
                if hasattr(cart, '_catalog') and cart._catalog:
                    try:
                        product = cart._catalog.get_product(item.product_id)
                        category_id = product.category_id
                    except Exception:
                        pass
                total += self._discount_engine.calculate_best_price(
                    item.unit_price, item.quantity, category_id
                )
            return total
        return cart.get_subtotal()

    def calculate_tax(self, cart):
        return self._tax_calculator.calculate(self.calculate_subtotal(cart))

    def calculate_total(self, cart):
        subtotal = self.calculate_subtotal(cart)
        tax = self._tax_calculator.calculate(subtotal)
        return subtotal + tax

    def calculate_shipping(self, total_weight):
        return total_weight * 0.5

    def apply_coupon(self, cart, coupon_code):
        subtotal = self.calculate_subtotal(cart)
        if self._coupon_manager:
            return self._coupon_manager.apply_coupon(coupon_code, subtotal)
        raise ValueError(f"No coupon manager configured")

    def get_price_breakdown(self, cart, coupon_code=None):
        subtotal = self.calculate_subtotal(cart)
        original_subtotal = cart.get_subtotal()
        discount = original_subtotal - subtotal
        tax = self._tax_calculator.calculate(subtotal)
        total = subtotal + tax

        result = {
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "item_count": cart.get_item_count(),
            "tax_rate": self._tax_calculator.get_rate(),
            "discount": discount,
        }

        if coupon_code and self._coupon_manager:
            coupon_discount_total = self._coupon_manager.apply_coupon(coupon_code, subtotal)
            coupon_discount = subtotal - coupon_discount_total
            result["coupon_discount"] = coupon_discount
            result["total"] = coupon_discount_total + tax

        return result
