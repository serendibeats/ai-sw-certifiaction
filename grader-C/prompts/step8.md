# Step 8: 데이터 검증 + 보고서 + 구조 정리

## 상품 데이터 검증 강화

### 검증 규칙
- `name`: 비어있으면 안 됨 (빈 문자열 또는 공백만 있는 문자열 불가)
- `price`: 0 이상이어야 함 (음수 불가)
- `weight`: 0 이상이어야 함 (음수 불가)
- 카테고리 ID가 지정된 경우, 카탈로그에 해당 카테고리가 등록되어 있어야 함

### 기존 코드 수정
- `ProductCatalog.add_product()`: 상품 추가 전에 검증합니다.
  검증 실패 시 `InvalidProductError`를 발생시킵니다.
- `ProductCatalog.update_product()`: 변경될 필드에 대해 검증합니다.
  예: `update_product(id, price=-10)` → `InvalidProductError`.

## `src/reports.py` — 보고서 생성

### ReportGenerator
- `__init__(self, catalog, inventory, review_manager=None)`: 의존성 주입.
- `inventory_report()`: dict 반환.
  - `"total_products"`: 카탈로그 상품 수
  - `"total_stock"`: 전체 재고 합계
  - `"low_stock_items"`: 재고 5개 이하 상품 ID 리스트
  - `"out_of_stock"`: 재고 0인 상품 ID 리스트
- `catalog_report()`: dict 반환.
  - `"by_category"`: `{category_id: count}` 딕셔너리
  - `"by_status"`: `{status_name: count}` 딕셔너리
  - `"price_range"`: `{"min": ..., "max": ..., "average": ...}`
- `top_rated_products(n=5)`: 평균 평점이 높은 순으로 n개 상품 리스트.
  ReviewManager가 없으면 빈 리스트.

## OrderService 확장: 주문 추적

- OrderService는 내부적으로 생성된 모든 주문을 `_orders` 딕셔너리에 보관합니다.
  (기존에 주문을 반환만 하고 보관하지 않았다면 수정이 필요합니다.)
- `get_order(order_id)`: 주문 조회.
- `get_all_orders()`: 모든 주문 리스트 (복사본).
- `get_orders_by_status(status)`: 특정 상태의 주문 리스트.

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py tests/test_step6.py tests/test_step7.py tests/test_step8.py -v
```
