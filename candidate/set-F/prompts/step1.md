# Step 1: 메시징 시스템 기반 구축

다음 파일들을 `src/` 아래에 구현하세요.

## `src/exceptions.py` — 커스텀 예외 클래스

- `UserNotFoundError(user_id)`: 사용자 미발견
- `ChannelNotFoundError(channel_id)`: 채널 미발견
- `MessageNotFoundError(message_id)`: 메시지 미발견
- `DuplicateUserError(username)`: 중복 사용자
- `DuplicateChannelError(channel_name)`: 중복 채널
- `InvalidMessageError(message)`: 유효하지 않은 메시지
- `InvalidChannelError(message)`: 유효하지 않은 채널
- `AccessDeniedError(message)`: 접근 거부
- `RateLimitError(user_id, message)`: 요청 속도 제한 초과
- `EncryptionError(message)`: 암호화 오류

각 예외는 관련 정보를 속성으로 저장하고 적절한 메시지를 가져야 합니다.

## `src/models.py` — 데이터 모델

### UserStatus (Enum)
- `ONLINE`, `OFFLINE`, `AWAY`, `DO_NOT_DISTURB`

### ChannelType (Enum)
- `PUBLIC`, `PRIVATE`, `DIRECT`

### User
- `id` (str, UUID 자동 생성), `username` (str), `display_name` (str, 기본값 "")
- `email` (str, 기본값 ""), `status` (UserStatus, 기본값 ONLINE)
- `created_at`, `updated_at` (float, 자동 설정 via `time.time()`)
- `metadata` (dict, 기본값 빈 딕셔너리)
- `to_dict()`, `update(**kwargs)`: updated_at 갱신
- `__eq__`, `__hash__`: id 기준

### Channel
- `id` (str, UUID 자동 생성), `name` (str), `description` (str, 기본값 "")
- `channel_type` (ChannelType, 기본값 PUBLIC), `creator_id` (str, optional)
- `created_at`, `updated_at`, `metadata`
- `members` (set, 기본값 빈 set)
- `to_dict()`, `update(**kwargs)`
- `__eq__`, `__hash__`: id 기준

### Message
- `id` (str, UUID 자동 생성), `channel_id` (str), `sender_id` (str), `content` (str)
- `created_at`, `updated_at`, `metadata`
- `edited` (bool, 기본값 False), `parent_id` (str, 기본값 None)
- `thread_count` (int, 기본값 0)
- `to_dict()`, `edit(new_content)`: content 변경, edited=True, updated_at 갱신

## `src/user_manager.py` — UserManager

내부적으로 `{user_id: User}` 딕셔너리로 관리합니다.

- `add_user(username, display_name="", email="")` → User: 중복 시 DuplicateUserError
- `get_user(user_id)` → User: 없으면 UserNotFoundError
- `get_user_by_username(username)` → User: 대소문자 구분 없이 검색
- `update_user(user_id, **kwargs)` → User
- `remove_user(user_id)`: 없으면 UserNotFoundError
- `list_users()` → list (방어적 복사)
- `set_status(user_id, status)` → User
- `search_users(query)` → list: 대소문자 구분 없이 username과 display_name 검색
- `count` → property: 사용자 수

## `src/channel_manager.py` — ChannelManager

내부적으로 `{channel_id: Channel}` 딕셔너리로 관리합니다.

- `create_channel(name, description="", channel_type=PUBLIC, creator_id=None)` → Channel
  - 채널명 중복 시 DuplicateChannelError
  - creator_id가 주어지면 자동으로 members에 추가
- `get_channel(channel_id)` → Channel: 없으면 ChannelNotFoundError
- `update_channel(channel_id, **kwargs)` → Channel
- `delete_channel(channel_id)`: 없으면 ChannelNotFoundError
- `list_channels()` → list (방어적 복사)
- `search_channels(query)` → list: 대소문자 구분 없이 name 검색
- `get_channels_by_type(channel_type)` → list
- `count` → property

## `src/message_manager.py` — MessageManager

- `__init__(self, channel_manager=None)`: ChannelManager 참조 저장
- `send_message(channel_id, sender_id, content)` → Message: 채널 존재 확인 (channel_manager가 있는 경우)
- `get_message(message_id)` → Message: 없으면 MessageNotFoundError
- `edit_message(message_id, new_content)` → Message
- `delete_message(message_id)`: 없으면 MessageNotFoundError
- `get_messages(channel_id)` → list: 채널의 모든 메시지, created_at 정렬
- `get_messages_by_user(user_id)` → list
- `search_messages(query)` → list: 대소문자 구분 없이 content 검색
- `count` → property

## `src/__init__.py` — 빈 파일

## 검증

```bash
pytest tests/test_step1.py -v
```
