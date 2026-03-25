from discounts import DiscountType


class Coupon:
    def __init__(self, code, discount_type, value, usage_limit=1, used_count=0, is_active=True):
        self.code = code
        self.discount_type = discount_type
        self.value = value
        self.usage_limit = usage_limit
        self.used_count = used_count
        self.is_active = is_active

    def is_valid(self):
        if not self.is_active:
            return False
        if self.usage_limit == 0:
            return True
        return self.used_count < self.usage_limit

    def apply(self, total):
        if self.discount_type == DiscountType.PERCENTAGE:
            return total * (1 - self.value)
        elif self.discount_type == DiscountType.FIXED_AMOUNT:
            return max(0, total - self.value)
        return total

    def use(self):
        self.used_count += 1


class CouponManager:
    def __init__(self):
        self._coupons = {}

    def add_coupon(self, coupon):
        if coupon.code in self._coupons:
            raise ValueError(f"Coupon with code {coupon.code} already exists")
        self._coupons[coupon.code] = coupon

    def get_coupon(self, code):
        return self._coupons.get(code, None)

    def validate_coupon(self, code):
        coupon = self._coupons.get(code)
        if coupon and coupon.is_valid():
            return True
        return False

    def apply_coupon(self, code, total):
        coupon = self._coupons.get(code)
        if not coupon or not coupon.is_valid():
            raise ValueError(f"Invalid coupon: {code}")
        result = coupon.apply(total)
        coupon.use()
        return result

    def remove_coupon(self, code):
        if code in self._coupons:
            del self._coupons[code]
