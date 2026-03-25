# Step 1: 상품 카탈로그 + 재고 관리 시스템

다음 파일들을 `src/` 아래에 구현하세요.

## `src/exceptions.py` — 커스텀 예외 클래스

- `ProductNotFoundError(product_id)`: 상품 미발견
- `DuplicateProductError(product_id)`: 중복 상품
- `InsufficientStockError(product_id, requested, available)`: 재고 부족
- `InvalidProductError(message)`: 유효하지 않은 상품 데이터
- `CategoryNotFoundError(category_id)`: 카테고리 미발견

각 예외는 관련 정보를 속성으로 저장하고, 적절한 메시지를 가져야 합니다.

## `src/models.py` — 데이터 모델

### ProductStatus (Enum)
- `ACTIVE`, `INACTIVE`, `DISCONTINUED`

### Category
- `id` (str), `name` (str), `parent_id` (str, optional, 기본값 None)
- `to_dict()`: 딕셔너리 변환
- `__eq__`, `__hash__`: id 기준 비교

### Product
- `id` (str), `name` (str), `description` (str, 기본값 "")
- `price` (float), `cost` (float, 기본값 0.0)
- `category_id` (str, optional)
- `status` (ProductStatus, 기본값 ACTIVE)
- `tags` (list of str, 기본값 빈 리스트)
- `created_at` (float, 자동 설정 via `time.time()`)
- `updated_at` (float, 자동 설정)
- `metadata` (dict, 기본값 빈 딕셔너리)
- `get_margin()`: `price - cost` 반환
- `is_available()`: status가 ACTIVE이면 True
- `to_dict()`: 모든 필드를 딕셔너리로 변환 (status는 문자열로)
- `update(**kwargs)`: 전달된 필드만 변경, `updated_at` 갱신
- `__eq__`, `__hash__`: id 기준

## `src/catalog.py` — ProductCatalog

내부적으로 상품을 딕셔너리(`{id: Product}`)로 저장합니다.

### 기본 CRUD
- `add_product(product)`: 추가. 중복 시 `DuplicateProductError`.
- `remove_product(product_id)`: 삭제. 없으면 `ProductNotFoundError`.
- `get_product(product_id)`: 조회. 없으면 `ProductNotFoundError`.
- `update_product(product_id, **kwargs)`: 필드 업데이트. 없으면 `ProductNotFoundError`.
- `list_products()`: 모든 상품 리스트.
- `count()`: 상품 수.

### 카테고리 관리
- `add_category(category)`: 카테고리 추가.
- `get_category(category_id)`: 카테고리 조회.
- `list_categories()`: 모든 카테고리 리스트.
- `get_products_by_category(category_id)`: 해당 카테고리 상품 리스트.

### 검색 및 필터
- `search(query)`: 이름에 query가 포함된 상품 리스트.
- `filter_by_status(status)`: 해당 상태의 상품 리스트.
- `filter_by_price_range(min_price, max_price)`: 가격 범위 필터 (경계 포함).
- `sort_products(field, ascending=True)`: 정렬. 지원: "name", "price", "created_at".

### 통계
- `get_statistics()`: dict 반환
  - `"total_products"`, `"active_products"`, `"average_price"`, `"total_value"` (price 합계)

## `src/inventory.py` — InventoryManager

내부적으로 재고를 `{product_id: int}` 딕셔너리로 관리합니다.

- `set_stock(product_id, quantity)`: 재고 설정 (0 이상).
- `get_stock(product_id)`: 재고 조회 (없으면 0).
- `adjust_stock(product_id, delta)`: 재고 조정 (+/-). 결과가 음수면 `InsufficientStockError`.
- `is_available(product_id, quantity=1)`: 해당 수량만큼 재고 있는지.
- `get_low_stock_items(threshold=5)`: 재고가 threshold 이하인 상품 ID 리스트.
- `get_all_stock()`: 전체 재고 딕셔너리 반환.
- `remove_product(product_id)`: 해당 상품 재고 정보 삭제.
- `get_total_items()`: 전체 재고 합계.

## `src/serializer.py` — 직렬화 유틸리티

- `serialize_product(product)`: Product → dict
- `deserialize_product(data)`: dict → Product
- `serialize_products(products)`: 리스트 직렬화
- `serialize_category(category)`: Category → dict

## 검증

```bash
pytest tests/test_step1.py -v
```
