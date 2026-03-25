from models import Product, Category, ProductStatus


def serialize_product(product):
    return product.to_dict()


def deserialize_product(data):
    d = dict(data)
    if "status" in d and isinstance(d["status"], str):
        d["status"] = ProductStatus(d["status"])
    return Product(**d)


def serialize_products(products):
    return [serialize_product(p) for p in products]


def serialize_category(category):
    return category.to_dict()
