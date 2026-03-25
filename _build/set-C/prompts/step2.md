# Step 2: 장바구니 + 가격 계산

기존 코드 위에 다음 파일들을 추가하세요.

## `src/cart.py` — ShoppingCart

### CartItem
- `product_id` (str)
- `product_name` (str): 추가 시점의 상품명 스냅샷
- `unit_price` (float): 추가 시점의 가격 스냅샷
- `quantity` (int)
- `get_subtotal()`: `unit_price * quantity`
- `to_dict()`: 딕셔너리 변환

### ShoppingCart
- `__init__(self, catalog)`: ProductCatalog 참조를 저장합니다.
- `add_item(product_id, quantity=1)`: 상품 추가.
  - 카탈로그에서 가격과 이름을 가져옵니다.
  - 이미 있는 상품이면 수량을 더합니다.
  - 존재하지 않는 상품이면 `ProductNotFoundError`.
- `remove_item(product_id)`: 상품 완전 제거. 없으면 False, 성공 시 True.
- `update_quantity(product_id, quantity)`: 수량 변경. 0이면 제거. 없으면 `ProductNotFoundError`.
- `get_item(product_id)`: CartItem 조회. 없으면 None.
- `get_items()`: 모든 CartItem 리스트.
- `get_subtotal()`: 총 소계 (모든 아이템의 subtotal 합).
- `get_item_count()`: 총 수량 합 (아이템 종류 수가 아닌 전체 수량).
- `clear()`: 장바구니 비우기.
- `is_empty()`: 비었는지 여부.
- `to_dict()`: 딕셔너리 변환

## `src/pricing.py` — PricingEngine

### TaxCalculator
- `__init__(self, rate=0.1)`: 세율 설정 (기본 10%)
- `calculate(amount)`: 세금 계산
- `get_rate()`: 현재 세율

### PricingEngine
- `__init__(self, tax_calculator=None)`: TaxCalculator 주입 (없으면 기본 10%)
- `calculate_subtotal(cart)`: 장바구니 소계
- `calculate_tax(cart)`: 세금
- `calculate_total(cart)`: 소계 + 세금
- `get_price_breakdown(cart)`: dict 반환
  - `"subtotal"`, `"tax"`, `"total"`, `"item_count"`, `"tax_rate"`

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py -v
```
