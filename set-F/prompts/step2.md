# Step 2: 알림 + 멘션 파싱

기존 코드 위에 다음 파일들을 추가하세요.

## `src/mention.py` — MentionParser

### MentionType (Enum)
- `USER`, `CHANNEL`, `ALL`

### MentionParser
- `parse(content)` → list: `@username` 패턴에서 사용자명 추출. `@all`, `@here`는 제외. 중복 제거.
- `parse_channel_mentions(content)` → list: `#channel` 패턴에서 채널명 추출.
- `parse_all_mentions(content)` → list: `@all` 또는 `@here`가 있으면 `[MentionType.ALL]` 반환.
- `parse_all_types(content)` → list of (MentionType, name) tuples: 모든 멘션 타입 파싱.

## `src/notification.py` — NotificationManager

### Notification 모델 (models.py에 추가)
- `id` (UUID), `user_id`, `notification_type` (str), `content` (str)
- `source_id` (str, optional), `read` (bool, 기본값 False), `created_at`
- `to_dict()`

### NotificationManager
- `__init__(self, user_manager=None)`
- `notify(user_id, notification_type, content, source_id=None)` → Notification
- `get_notifications(user_id)` → list (방어적 복사)
- `get_unread_count(user_id)` → int
- `mark_read(notification_id)`: 단일 알림 읽음 처리
- `mark_all_read(user_id)`: 해당 사용자의 모든 알림 읽음 처리
- `clear_notifications(user_id)`: 해당 사용자의 모든 알림 삭제

## MessageManager 통합

MessageManager에 멘션 파싱을 통합합니다:

- `__init__`에 `mention_parser=None`, `notification_manager=None` 파라미터 추가
- `send_message()`에서:
  - mention_parser와 notification_manager가 설정된 경우
  - content에서 @username 멘션 파싱
  - 각 멘션된 사용자에게 "mention" 타입 알림 생성
  - notification_manager의 user_manager를 통해 username → user_id 변환

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py -v
```
