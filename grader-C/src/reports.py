class ReportGenerator:
    def __init__(self, catalog, inventory, review_manager=None):
        self._catalog = catalog
        self._inventory = inventory
        self._review_manager = review_manager

    def inventory_report(self):
        products = self._catalog.list_products()
        all_stock = self._inventory.get_all_stock()
        total_stock = self._inventory.get_total_items()
        low_stock = self._inventory.get_low_stock_items(threshold=5)
        out_of_stock = [p.id for p in products if self._inventory.get_stock(p.id) == 0]
        return {
            "total_products": len(products),
            "total_stock": total_stock,
            "low_stock_items": low_stock,
            "out_of_stock": out_of_stock,
        }

    def catalog_report(self):
        products = self._catalog.list_products()
        by_category = {}
        for p in products:
            cat = p.category_id
            by_category[cat] = by_category.get(cat, 0) + 1

        by_status = {}
        for p in products:
            status_name = p.status.value
            by_status[status_name] = by_status.get(status_name, 0) + 1

        prices = [p.price for p in products]
        if prices:
            price_range = {
                "min": min(prices),
                "max": max(prices),
                "average": sum(prices) / len(prices),
            }
        else:
            price_range = {"min": 0, "max": 0, "average": 0}

        return {
            "by_category": by_category,
            "by_status": by_status,
            "price_range": price_range,
        }

    def top_rated_products(self, n=5):
        if not self._review_manager:
            return []
        products = self._catalog.list_products()
        rated = [(p, self._review_manager.get_average_rating(p.id)) for p in products]
        rated = [(p, r) for p, r in rated if r > 0]
        rated.sort(key=lambda x: x[1], reverse=True)
        return [p for p, r in rated[:n]]
