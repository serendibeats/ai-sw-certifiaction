# Step 7: 쿠폰 시스템 + 주문 환불

## `src/coupons.py` — 쿠폰 시스템

### Coupon
- `code` (str): 고유 쿠폰 코드
- `discount_type` (DiscountType): 할인 유형 (PERCENTAGE 또는 FIXED_AMOUNT)
- `value` (float): 할인 값
- `usage_limit` (int, 기본값 1): 사용 가능 횟수 (0 = 무제한)
- `used_count` (int, 기본값 0): 사용된 횟수
- `is_active` (bool, 기본값 True)
- `is_valid()`: 활성이고 사용 한도 미달이면 True. `usage_limit=0`이면 무제한.
- `apply(total)`: 할인 적용 금액 반환.
  - PERCENTAGE: `total * (1 - value)`
  - FIXED_AMOUNT: `max(0, total - value)`
- `use()`: 사용 횟수 1 증가.

### CouponManager
- `add_coupon(coupon)`: 등록. 같은 code 존재 시 `ValueError`.
- `get_coupon(code)`: 조회. 없으면 `None`.
- `validate_coupon(code)`: 유효하면 `True`, 아니면 `False`.
- `apply_coupon(code, total)`: 쿠폰 적용. 유효하지 않으면 `ValueError`. 사용 횟수 증가.
- `remove_coupon(code)`: 삭제.

## 주문 환불 기능

### OrderStatus 확장
- `REFUNDED` 상태를 추가합니다.
- 유효 전이 추가: `DELIVERED → REFUNDED`

### Order 확장
- `refund_amount` (float, 기본값 0.0): 환불 금액
- `refunded_at` (float, optional): 환불 시각

### OrderService 확장
- `refund_order(order, amount=None)`: 주문 환불.
  - `amount`가 None이면 전액 환불 (`order.get_total()`).
  - `amount`가 지정되면 부분 환불.
  - 상태를 `REFUNDED`로 전이합니다.
  - 전액 환불 시 재고를 복원합니다 (`adjust_stock`으로 각 라인의 quantity만큼 복원).
  - `order.refund_amount`를 설정합니다.
  - 이벤트 버스 설정 시 `order_refunded` 이벤트 발행 (`{"order_id": ..., "amount": ...}`).
  - 환불 금액이 주문 총액을 초과하거나 음수인 경우 ValueError를 발생시킵니다.
  - 환불 불가능한 상태면 `ValueError`.

## PricingEngine 확장
- `__init__`에 `coupon_manager` 파라미터 추가 (optional, 기본값 None).
- `apply_coupon(cart, coupon_code)`: 쿠폰을 적용한 최종 금액 반환.
  - 먼저 `calculate_subtotal(cart)`로 소계를 구하고, 쿠폰을 적용합니다.
- `get_price_breakdown(cart, coupon_code=None)`: 쿠폰 적용 시 `"coupon_discount"` 필드 추가.

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py tests/test_step6.py tests/test_step7.py -v
```
