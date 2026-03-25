# Step 4: 이벤트 시스템 + 감사 추적

## `src/events.py` — 이벤트 버스

### Event
- `type` (str): 이벤트 타입
- `data` (dict): 이벤트 데이터
- `timestamp` (float): 발생 시각

### EventBus
- `subscribe(event_type, callback)`: 이벤트 구독. callback은 `(event) -> None`.
- `publish(event_type, data)`: 이벤트 발행. 등록된 모든 콜백 호출. 이벤트 데이터는 독립적인 복사본으로 저장되어야 합니다.
- `get_history()`: 발행된 모든 이벤트 리스트 (시간순).
- `get_history_by_type(event_type)`: 특정 타입 이벤트만.
- `clear_history()`: 이력 초기화.
- `clear_subscribers()`: 구독자 초기화.

### 필수 이벤트 목록
| 이벤트 타입 | 발생 시점 | data 필드 |
|---|---|---|
| `product_added` | 카탈로그에 상품 추가 | `{"product_id": ...}` |
| `product_removed` | 카탈로그에서 상품 삭제 | `{"product_id": ...}` |
| `product_updated` | 상품 정보 변경 | `{"product_id": ..., "changes": {...}}` |
| `stock_changed` | 재고 변경 | `{"product_id": ..., "old_stock": ..., "new_stock": ...}` |
| `cart_item_added` | 장바구니에 상품 추가 | `{"product_id": ..., "quantity": ...}` |
| `cart_item_removed` | 장바구니에서 상품 제거 | `{"product_id": ...}` |
| `order_created` | 주문 생성 | `{"order_id": ...}` |
| `order_status_changed` | 주문 상태 변경 | `{"order_id": ..., "old_status": ..., "new_status": ...}` |

## 기존 코드 수정

- `ProductCatalog`에 `event_bus` 파라미터 추가 (optional, 기본값 None).
  이벤트 버스가 설정되면 상품 추가/삭제/수정 시 이벤트를 발행합니다.
- `InventoryManager`에 `event_bus` 파라미터 추가.
  재고 변경 시 `stock_changed` 이벤트를 발행합니다.
- `ShoppingCart`에 `event_bus` 파라미터 추가.
  장바구니 아이템 추가/제거 시 이벤트를 발행합니다.
- `OrderService`에 `event_bus` 파라미터 추가.
  주문 생성 시 `order_created`, 상태 변경 시 `order_status_changed` 이벤트를 발행합니다.

## 장바구니 재고 확인 추가

`ShoppingCart`에 `inventory` 파라미터를 추가합니다 (optional, 기본값 None).
인벤토리가 설정된 경우, `add_item()` 시 재고가 충분한지 확인합니다.
재고가 부족하면 `InsufficientStockError`를 발생시킵니다.

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py -v
```
