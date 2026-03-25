# Step 5: 소프트 삭제 + 레이트 리미팅

## 소프트 삭제

기존의 삭제 동작을 하드 삭제에서 **소프트 삭제**로 전환합니다.

### Message 모델 확장
- `is_deleted` (bool, 기본값 False)
- `deleted_at` (float, 기본값 None)

### Channel 모델 확장
- `is_deleted` (bool, 기본값 False)
- `deleted_at` (float, 기본값 None)

### MessageManager 수정
- `delete_message()`: is_deleted=True, deleted_at=time.time() 설정 (소프트 삭제)
- `get_message()`: 삭제된 메시지는 MessageNotFoundError
- `get_messages()`: 삭제된 메시지 필터링
- `get_all_messages()`: 삭제된 메시지 필터링
- `get_messages_by_user()`: 삭제된 메시지 필터링
- `search_messages()`: 삭제된 메시지 제외
- `get_deleted_messages(channel_id)` → list: 소프트 삭제된 메시지 목록
- `purge_message(message_id)`: 실제 하드 삭제 (저장소에서 완전 제거)
- `count`: 삭제되지 않은 메시지만 카운트

### ChannelManager 수정
- `delete_channel()`: 소프트 삭제
- `get_channel()`: 삭제된 채널은 ChannelNotFoundError
- `list_channels()`: 삭제된 채널 필터링
- `search_channels()`: 삭제된 채널 제외
- `get_deleted_channels()` → list: 소프트 삭제된 채널 목록
- `count`: 삭제되지 않은 채널만 카운트
- 삭제된 채널명으로 새 채널 생성 가능

## RateLimiter

`src/message_manager.py`에 추가하거나 별도 파일로 구현합니다.

### RateLimiter
- `__init__(self, max_requests, window_seconds)`: 슬라이딩 윈도우 방식
- `check(user_id)` → bool: 제한 내이면 True
- `record(user_id)`: 요청 기록
- `get_remaining(user_id)` → int: 남은 요청 수

### MessageManager 통합
- `__init__`에 `rate_limiter=None` 추가
- `send_message()`: rate_limiter가 설정된 경우 확인, 초과 시 RateLimitError

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py -v
```
