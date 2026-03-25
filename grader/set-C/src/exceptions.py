class ProductNotFoundError(Exception):
    def __init__(self, product_id):
        self.product_id = product_id
        super().__init__(f"Product not found: {product_id}")


class DuplicateProductError(Exception):
    def __init__(self, product_id):
        self.product_id = product_id
        super().__init__(f"Duplicate product: {product_id}")


class InsufficientStockError(Exception):
    def __init__(self, product_id, requested, available):
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for {product_id}: requested {requested}, available {available}"
        )


class InvalidProductError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class CategoryNotFoundError(Exception):
    def __init__(self, category_id):
        self.category_id = category_id
        super().__init__(f"Category not found: {category_id}")
