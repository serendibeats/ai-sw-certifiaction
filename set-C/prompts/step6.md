# Step 6: 상품 리뷰 + 위시리스트

## `src/reviews.py` — 리뷰 시스템

### Review
- `id` (str), `product_id` (str), `user_id` (str)
- `rating` (int, 1~5), `comment` (str, 기본값 "")
- `created_at` (float, 자동 설정)
- `to_dict()`: 딕셔너리 변환

### ReviewManager
- `add_review(review)`: 리뷰 추가. 같은 사용자가 같은 상품에 중복 리뷰 시 `ValueError`.
- `get_reviews(product_id)`: 해당 상품의 모든 리뷰 리스트 (시간순).
- `get_average_rating(product_id)`: 평균 평점. 리뷰 없으면 `0.0`.
- `get_review_count(product_id)`: 리뷰 수.
- `remove_review(review_id)`: 리뷰 삭제. 없으면 `False`, 성공 시 `True`.
- 이벤트 버스가 설정된 경우 `review_added` 이벤트 발행 (`{"product_id": ..., "rating": ...}`).

## `src/wishlist.py` — 위시리스트

### Wishlist
- `__init__(self, user_id, catalog=None, event_bus=None)`: 사용자별 위시리스트.
- `add_item(product_id)`: 상품 추가. 이미 있으면 무시. 카탈로그 설정 시 존재 여부 확인.
- `remove_item(product_id)`: 제거. 없으면 `False`.
- `get_items()`: 상품 ID 리스트 반환 (복사본).
- `contains(product_id)`: 포함 여부.
- `count()`: 아이템 수.
- `move_to_cart(product_id, cart)`: 위시리스트에서 제거하고 장바구니에 추가.
- 이벤트 버스 설정 시 `wishlist_item_added`, `wishlist_item_removed` 이벤트 발행.

## 기존 코드 수정

### ProductCatalog 확장
- `sort_products()`: `"rating"` 필드 지원 추가. ReviewManager 참조가 필요합니다.
  - `__init__`에 `review_manager` 파라미터 추가 (optional, 기본값 None).
  - rating 정렬 시 `review_manager.get_average_rating(product.id)` 사용.
- `get_statistics()`에 `"average_rating"` 추가 (전체 상품의 평균 평점, ReviewManager 사용).

### Serializer 확장
- `serialize_product()`와 `deserialize_product()`에서 `weight` 필드를 처리해야 합니다.
  (Step 3에서 Product에 weight를 추가했지만, serializer가 아직 이를 처리하지 않을 수 있습니다.)
- 리뷰 정보는 직렬화에 포함하지 않습니다 (별도 관리).

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py tests/test_step6.py -v
```
