"""Step 6: Reviews + Wishlist."""
import pytest
from models import Product
from catalog import ProductCatalog
from cart import ShoppingCart
from reviews import Review, ReviewManager
from wishlist import Wishlist
from events import EventBus


class TestReviews:
    def test_add_review(self):
        rm = ReviewManager()
        rm.add_review(Review(id="r1", product_id="p1", user_id="u1", rating=5, comment="Great!"))
        assert rm.get_review_count("p1") == 1

    def test_duplicate_user_review_raises(self):
        rm = ReviewManager()
        rm.add_review(Review(id="r1", product_id="p1", user_id="u1", rating=5))
        with pytest.raises(ValueError):
            rm.add_review(Review(id="r2", product_id="p1", user_id="u1", rating=3))

    def test_average_rating(self):
        rm = ReviewManager()
        rm.add_review(Review(id="r1", product_id="p1", user_id="u1", rating=5))
        rm.add_review(Review(id="r2", product_id="p1", user_id="u2", rating=3))
        assert rm.get_average_rating("p1") == 4.0

    def test_no_reviews_rating(self):
        rm = ReviewManager()
        assert rm.get_average_rating("p1") == 0.0

    def test_review_event(self):
        bus = EventBus()
        rm = ReviewManager(event_bus=bus)
        rm.add_review(Review(id="r1", product_id="p1", user_id="u1", rating=4))
        events = bus.get_history_by_type("review_added")
        assert len(events) == 1

    def test_remove_review(self):
        rm = ReviewManager()
        rm.add_review(Review(id="r1", product_id="p1", user_id="u1", rating=5))
        assert rm.remove_review("r1") is True
        assert rm.get_review_count("p1") == 0


class TestWishlist:
    def test_add_remove(self):
        wl = Wishlist(user_id="u1")
        wl.add_item("p1")
        assert wl.contains("p1") is True
        assert wl.remove_item("p1") is True
        assert wl.contains("p1") is False

    def test_duplicate_ignored(self):
        wl = Wishlist(user_id="u1")
        wl.add_item("p1")
        wl.add_item("p1")
        assert wl.count() == 1

    def test_move_to_cart(self):
        cat = ProductCatalog()
        cat.add_product(Product(id="p1", name="W", price=10.0))
        wl = Wishlist(user_id="u1", catalog=cat)
        wl.add_item("p1")
        cart = ShoppingCart(cat)
        wl.move_to_cart("p1", cart)
        assert wl.contains("p1") is False
        assert cart.get_item("p1") is not None

    def test_get_items_returns_copy(self):
        wl = Wishlist(user_id="u1")
        wl.add_item("p1")
        items = wl.get_items()
        items.clear()
        assert wl.count() == 1


class TestCatalogRatingIntegration:
    def test_sort_by_rating(self):
        rm = ReviewManager()
        cat = ProductCatalog(review_manager=rm)
        cat.add_product(Product(id="p1", name="A", price=10.0))
        cat.add_product(Product(id="p2", name="B", price=20.0))
        rm.add_review(Review(id="r1", product_id="p1", user_id="u1", rating=3))
        rm.add_review(Review(id="r2", product_id="p2", user_id="u1", rating=5))
        sorted_p = cat.sort_products("rating", ascending=False)
        assert sorted_p[0].id == "p2"

    def test_statistics_include_rating(self):
        rm = ReviewManager()
        cat = ProductCatalog(review_manager=rm)
        cat.add_product(Product(id="p1", name="A", price=10.0))
        rm.add_review(Review(id="r1", product_id="p1", user_id="u1", rating=4))
        stats = cat.get_statistics()
        assert "average_rating" in stats
