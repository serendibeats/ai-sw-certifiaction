import time


class Review:
    def __init__(self, id, product_id, user_id, rating, comment="", created_at=None):
        self.id = id
        self.product_id = product_id
        self.user_id = user_id
        self.rating = rating
        self.comment = comment
        self.created_at = created_at if created_at is not None else time.time()

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at,
        }


class ReviewManager:
    def __init__(self, event_bus=None):
        self._reviews = {}  # {review_id: Review}
        self._event_bus = event_bus

    def add_review(self, review):
        # Check for duplicate (same user + same product)
        for existing in self._reviews.values():
            if existing.user_id == review.user_id and existing.product_id == review.product_id:
                raise ValueError(f"User {review.user_id} already reviewed product {review.product_id}")
        self._reviews[review.id] = review
        if self._event_bus:
            self._event_bus.publish("review_added", {
                "product_id": review.product_id,
                "rating": review.rating,
            })

    def get_reviews(self, product_id):
        reviews = [r for r in self._reviews.values() if r.product_id == product_id]
        return sorted(reviews, key=lambda r: r.created_at)

    def get_average_rating(self, product_id):
        reviews = [r for r in self._reviews.values() if r.product_id == product_id]
        if not reviews:
            return 0.0
        return sum(r.rating for r in reviews) / len(reviews)

    def get_review_count(self, product_id):
        return sum(1 for r in self._reviews.values() if r.product_id == product_id)

    def remove_review(self, review_id):
        if review_id not in self._reviews:
            return False
        del self._reviews[review_id]
        return True
