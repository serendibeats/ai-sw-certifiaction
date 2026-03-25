# Step 5: 할인 시스템 + 재고 예약 + 구조 변경

## `src/discounts.py` — 할인 엔진

### DiscountType (Enum)
- `PERCENTAGE`: 비율 할인 (예: 10% 할인)
- `FIXED_AMOUNT`: 고정 금액 할인 (예: 1000원 할인)
- `BUY_X_GET_Y`: X개 구매 시 Y개 무료

### Discount
- `id` (str), `name` (str), `discount_type` (DiscountType)
- `value` (float): 할인율 또는 금액
- `min_quantity` (int, 기본값 0): 최소 수량 조건
- `applicable_category_ids` (list of str, 기본값 빈 리스트): 적용 카테고리 (빈 리스트 = 전체)
- `is_active` (bool, 기본값 True)
- `apply(unit_price, quantity, category_id=None)`: 할인 적용된 총 금액 반환
  - PERCENTAGE: `unit_price * quantity * (1 - value)`
  - FIXED_AMOUNT: `max(0, unit_price * quantity - value)`
  - BUY_X_GET_Y: value는 (X, Y) 튜플. X+Y개마다 Y개 무료. 나머지는 정상가.
- `is_applicable(quantity, category_id=None)`: 적용 가능 여부

### DiscountEngine
- `add_discount(discount)`: 할인 등록
- `remove_discount(discount_id)`: 할인 삭제
- `get_applicable_discounts(product_id, quantity, category_id=None)`: 적용 가능한 할인 리스트
- `calculate_best_price(unit_price, quantity, category_id=None)`: 가장 유리한 할인 적용 금액

## PricingEngine 변경

- PricingEngine에 `discount_engine` 파라미터를 추가합니다 (optional).
- `calculate_subtotal(cart)`는 이제 할인이 적용된 소계를 반환합니다.
  - 각 CartItem에 대해 `discount_engine.calculate_best_price()` 사용
  - 할인 엔진이 없으면 기존 방식대로 계산
- `get_price_breakdown(cart)`에 `"discount"` (총 할인 금액) 필드를 추가합니다.

## 재고 예약: InventoryManager 확장

기존 `InventoryManager`에 예약 기능을 추가합니다:

- `reserve(product_id, quantity)`: 재고에서 지정량을 예약합니다.
  - 가용 재고(= 총 재고 - 예약된 수량)가 부족하면 `InsufficientStockError`.
  - 예약 ID (str)를 반환합니다.
- `release(reservation_id)`: 예약을 취소합니다 (예약된 수량을 가용으로 복원).
- `confirm(reservation_id)`: 예약을 확정합니다 (실제 재고에서 차감).
- `get_available_stock(product_id)`: 가용 재고 (총 재고 - 예약량).

## ShoppingCart 변경

인벤토리가 설정된 ShoppingCart에서:
- `add_item()`: 재고를 **예약**합니다 (직접 차감하지 않음).
- `remove_item()`: 해당 예약을 **해제**합니다.
- `update_quantity()`: 기존 예약 해제 후 새 수량으로 재예약.
- 내부적으로 `{product_id: reservation_id}` 매핑을 관리합니다.

## OrderService 변경

- `create_order()`:
  - 기존: `inventory.adjust_stock`으로 직접 차감 → **삭제**
  - 변경: 장바구니의 예약을 `confirm`으로 확정합니다.
- `cancel_order()`:
  - 기존: 재고 복원 → **삭제**
  - 변경: 이미 확정된 재고는 `adjust_stock`으로 복원합니다.

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py -v
```
