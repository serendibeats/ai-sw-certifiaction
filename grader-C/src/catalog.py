from exceptions import (
    DuplicateProductError,
    ProductNotFoundError,
    CategoryNotFoundError,
    InvalidProductError,
)
from models import ProductStatus


class ProductCatalog:
    def __init__(self, event_bus=None, review_manager=None):
        self._products = {}
        self._categories = {}
        self._event_bus = event_bus
        self._review_manager = review_manager

    def _validate_product(self, product):
        if not product.name or not product.name.strip():
            raise InvalidProductError("Product name cannot be empty")
        if product.price < 0:
            raise InvalidProductError("Product price cannot be negative")
        if product.weight < 0:
            raise InvalidProductError("Product weight cannot be negative")
        if product.category_id is not None and self._categories and product.category_id not in self._categories:
            raise InvalidProductError(f"Category {product.category_id} not found")

    def _validate_updates(self, **kwargs):
        if "name" in kwargs:
            if not kwargs["name"] or not kwargs["name"].strip():
                raise InvalidProductError("Product name cannot be empty")
        if "price" in kwargs and kwargs["price"] < 0:
            raise InvalidProductError("Product price cannot be negative")
        if "weight" in kwargs and kwargs["weight"] < 0:
            raise InvalidProductError("Product weight cannot be negative")
        if "category_id" in kwargs and kwargs["category_id"] is not None and self._categories:
            if kwargs["category_id"] not in self._categories:
                raise InvalidProductError(f"Category {kwargs['category_id']} not found")

    # Basic CRUD
    def add_product(self, product):
        if product.id in self._products:
            raise DuplicateProductError(product.id)
        self._validate_product(product)
        self._products[product.id] = product
        if self._event_bus:
            self._event_bus.publish("product_added", {"product_id": product.id})

    def remove_product(self, product_id):
        if product_id not in self._products:
            raise ProductNotFoundError(product_id)
        del self._products[product_id]
        if self._event_bus:
            self._event_bus.publish("product_removed", {"product_id": product_id})

    def get_product(self, product_id):
        if product_id not in self._products:
            raise ProductNotFoundError(product_id)
        return self._products[product_id]

    def update_product(self, product_id, **kwargs):
        if product_id not in self._products:
            raise ProductNotFoundError(product_id)
        self._validate_updates(**kwargs)
        self._products[product_id].update(**kwargs)
        if self._event_bus:
            self._event_bus.publish("product_updated", {"product_id": product_id, "changes": kwargs})

    def list_products(self):
        return list(self._products.values())

    def count(self):
        return len(self._products)

    # Category management
    def add_category(self, category):
        self._categories[category.id] = category

    def get_category(self, category_id):
        if category_id not in self._categories:
            raise CategoryNotFoundError(category_id)
        return self._categories[category_id]

    def list_categories(self):
        return list(self._categories.values())

    def get_products_by_category(self, category_id):
        return [p for p in self._products.values() if p.category_id == category_id]

    # Search and filter
    def search(self, query):
        query_lower = query.lower()
        return [p for p in self._products.values() if query_lower in p.name.lower()]

    def filter_by_status(self, status):
        return [p for p in self._products.values() if p.status == status]

    def filter_by_tag(self, tag):
        tag_lower = tag.lower()
        return [p for p in self._products.values() if any(t.lower() == tag_lower for t in p.tags)]

    def filter_by_price_range(self, min_price, max_price):
        return [p for p in self._products.values() if min_price <= p.price <= max_price]

    def sort_products(self, field, ascending=True):
        if field == "rating" and self._review_manager:
            return sorted(self._products.values(),
                          key=lambda p: self._review_manager.get_average_rating(p.id),
                          reverse=not ascending)
        return sorted(self._products.values(), key=lambda p: getattr(p, field), reverse=not ascending)

    # Statistics
    def get_statistics(self):
        products = list(self._products.values())
        total = len(products)
        active = sum(1 for p in products if p.status == ProductStatus.ACTIVE)
        avg_price = sum(p.price for p in products) / total if total > 0 else 0
        total_value = sum(p.price for p in products)
        stats = {
            "total_products": total,
            "active_products": active,
            "average_price": avg_price,
            "total_value": total_value,
        }
        if self._review_manager:
            ratings = [self._review_manager.get_average_rating(p.id) for p in products]
            non_zero = [r for r in ratings if r > 0]
            stats["average_rating"] = sum(non_zero) / len(non_zero) if non_zero else 0.0
        return stats
