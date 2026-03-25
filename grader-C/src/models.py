import time
from enum import Enum


class ProductStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DISCONTINUED = "DISCONTINUED"


class Category:
    def __init__(self, id: str, name: str, parent_id: str = None):
        self.id = id
        self.name = name
        self.parent_id = parent_id

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
        }

    def __eq__(self, other):
        if not isinstance(other, Category):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class Product:
    def __init__(self, id: str, name: str, description: str = "",
                 price: float = 0.0, cost: float = 0.0,
                 category_id: str = None,
                 status: ProductStatus = ProductStatus.ACTIVE,
                 tags: list = None,
                 created_at: float = None,
                 updated_at: float = None,
                 metadata: dict = None,
                 weight: float = 0.0):
        self.id = id
        self.name = name
        self.description = description
        self.price = price
        self.cost = cost
        self.category_id = category_id
        self.status = status
        self.tags = tags if tags is not None else []
        self.created_at = created_at if created_at is not None else time.time()
        self.updated_at = updated_at if updated_at is not None else time.time()
        self.metadata = metadata if metadata is not None else {}
        self.weight = weight

    def get_margin(self):
        return self.price - self.cost

    def is_available(self):
        return self.status == ProductStatus.ACTIVE

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "cost": self.cost,
            "category_id": self.category_id,
            "status": self.status.value,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
            "weight": self.weight,
        }

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.updated_at = time.time()

    def __eq__(self, other):
        if not isinstance(other, Product):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)
