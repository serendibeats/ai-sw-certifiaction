from enum import Enum


class DiscountType(Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    BUY_X_GET_Y = "buy_x_get_y"


class Discount:
    def __init__(self, id, name, discount_type, value, min_quantity=0,
                 applicable_category_ids=None, is_active=True):
        self.id = id
        self.name = name
        self.discount_type = discount_type
        self.value = value
        self.min_quantity = min_quantity
        self.applicable_category_ids = applicable_category_ids if applicable_category_ids is not None else []
        self.is_active = is_active

    def apply(self, unit_price, quantity, category_id=None):
        if not self.is_applicable(quantity, category_id):
            return unit_price * quantity

        if self.discount_type == DiscountType.PERCENTAGE:
            return unit_price * quantity * (1 - self.value)
        elif self.discount_type == DiscountType.FIXED_AMOUNT:
            return max(0, unit_price * quantity - self.value)
        elif self.discount_type == DiscountType.BUY_X_GET_Y:
            x, y = self.value
            group_size = x + y
            full_groups = quantity // group_size
            remainder = quantity % group_size
            paid_items = full_groups * x + remainder
            return unit_price * paid_items

        return unit_price * quantity

    def is_applicable(self, quantity, category_id=None):
        if not self.is_active:
            return False
        if quantity < self.min_quantity:
            return False
        if self.applicable_category_ids and category_id not in self.applicable_category_ids:
            return False
        return True


class DiscountEngine:
    def __init__(self):
        self._discounts = {}

    def add_discount(self, discount):
        self._discounts[discount.id] = discount

    def remove_discount(self, discount_id):
        if discount_id in self._discounts:
            del self._discounts[discount_id]

    def get_applicable_discounts(self, product_id, quantity, category_id=None):
        return [d for d in self._discounts.values() if d.is_applicable(quantity, category_id)]

    def calculate_best_price(self, unit_price, quantity, category_id=None):
        original = unit_price * quantity
        best = original
        for discount in self._discounts.values():
            if discount.is_applicable(quantity, category_id):
                price = discount.apply(unit_price, quantity, category_id)
                if price < best:
                    best = price
        return best
