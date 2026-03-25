# Step 3: 주문 시스템 + 시스템 정책

## 시스템 정책 (기존 코드 포함 전체 적용)

다음 정책은 이미 구현된 코드를 포함하여 **시스템 전체**에 적용됩니다:

1. **모든 문자열 검색/비교는 대소문자를 구분하지 않습니다.**
2. **컬렉션을 반환하는 모든 메서드는 내부 데이터의 복사본을 반환해야 합니다.**
   반환된 리스트/딕셔너리를 수정해도 원본에 영향이 없어야 합니다.

## Product 모델 확장

주문 시 배송비 계산을 위해 Product에 `weight` (float, 기본값 0.0) 필드가 필요합니다.
기존 코드와 호환되도록 기본값을 설정하세요.

## `src/order.py` — 주문 모델

### OrderStatus (Enum)
- `PENDING`, `CONFIRMED`, `SHIPPED`, `DELIVERED`, `CANCELLED`

### 유효한 전이
- PENDING → CONFIRMED, CANCELLED
- CONFIRMED → SHIPPED, CANCELLED
- SHIPPED → DELIVERED
- DELIVERED, CANCELLED → (최종 상태, 전이 불가)

### OrderLine
- `product_id`, `product_name`, `unit_price`, `quantity`, `weight`
- `get_subtotal()`: unit_price * quantity
- `get_total_weight()`: weight * quantity

### Order
- `id` (str), `lines` (list of OrderLine), `status` (OrderStatus, 기본값 PENDING)
- `created_at`, `updated_at` (자동 설정)
- `shipping_cost` (float, 기본값 0.0)
- `tax` (float, 기본값 0.0)
- `transition_to(new_status)`: 상태 전이. 유효하지 않으면 False 반환.
- `get_subtotal()`: 모든 라인의 소계 합
- `get_total()`: 소계 + 세금 + 배송비
- `get_total_weight()`: 모든 라인의 총 무게
- `to_dict()`

## `src/order_service.py` — OrderService

- `__init__(self, catalog, inventory, pricing_engine)`: 의존성 주입
- `create_order(cart, shipping_address=None)`: 장바구니에서 주문 생성.
  - 각 CartItem을 OrderLine으로 변환 (카탈로그에서 weight 조회)
  - 재고 차감 (`inventory.adjust_stock`)
  - 배송비 계산: `총 무게 * 0.5` (kg당 0.5원)
  - 세금 계산: PricingEngine 사용
  - 주문 ID 자동 생성
  - 장바구니 비우기
- `cancel_order(order)`: 주문 취소.
  - 상태를 CANCELLED로 전이
  - 재고 복원
- `get_order_summary(order)`: dict 반환
  - `"order_id"`, `"status"`, `"item_count"`, `"subtotal"`, `"tax"`, `"shipping"`, `"total"`

## PricingEngine 확장

- `calculate_shipping(total_weight)`: 배송비 계산 (총무게 × 0.5)
- 기존 `calculate_total(cart)`에 배송비를 포함하는 것은 **하지 않습니다** (주문 서비스에서 별도 처리).

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py -v
```
