# Step 4: 메시지 스레딩

## `src/thread_manager.py` — ThreadManager

- `__init__(self, message_manager=None, notification_manager=None)`
- `reply(parent_id, channel_id, sender_id, content)` → Message
  - parent_id 메시지가 존재해야 함 (MessageNotFoundError)
  - 대댓글은 원본 루트 메시지의 스레드에 통합 (parent의 parent_id가 있으면 root로 매핑)
  - 루트 메시지의 thread_count 증가
- `get_thread(message_id)` → list: 해당 메시지의 답글 목록, created_at 정렬
- `get_thread_count(message_id)` → int
- `get_thread_participants(message_id)` → set of user_ids

## 기존 코드 수정

### Message 모델
- `parent_id` (str, 기본값 None): 이미 있으면 활용, 없으면 추가
- `thread_count` (int, 기본값 0)

### MessageManager
- `get_messages(channel_id)`: **루트 메시지만 반환** (parent_id가 None인 것)
- `get_all_messages(channel_id)` → list: 루트 + 답글 모두 포함
- `search_messages(query)`: **모든 메시지 검색** (루트 + 답글)
- `count`: 모든 메시지 수 (루트 + 답글)

### NotificationManager 통합
- 스레드에 답글이 달리면 스레드 참여자들에게 "thread_reply" 알림 (발신자 제외)

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py -v
```
