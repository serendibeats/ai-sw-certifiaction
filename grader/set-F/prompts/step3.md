# Step 3: 접근 제어 시스템

## 시스템 정책 (기존 코드 포함 전체 적용)

다음 정책은 이미 구현된 코드를 포함하여 **시스템 전체**에 적용됩니다:

1. **모든 문자열 검색/비교는 대소문자를 구분하지 않습니다.**
2. **컬렉션을 반환하는 모든 메서드는 내부 데이터의 방어적 복사본을 반환해야 합니다.**
   반환된 리스트/딕셔너리를 수정해도 원본에 영향이 없어야 합니다.

## `src/access_control.py` — AccessController

- `__init__(self, user_manager=None, channel_manager=None)`
- `join_channel(user_id, channel_id)`: PUBLIC 채널은 누구나, PRIVATE 채널은 초대된 사용자만
- `leave_channel(user_id, channel_id)`: 채널 탈퇴
- `invite_to_channel(inviter_id, user_id, channel_id)`: PRIVATE 채널은 기존 멤버만 초대 가능
- `get_members(channel_id)` → list (방어적 복사)
- `is_member(user_id, channel_id)` → bool
- `can_access(user_id, channel_id)` → bool: PUBLIC은 항상 True, PRIVATE/DIRECT는 멤버만

## 기존 코드 수정

### ChannelManager
- `create_channel()`: creator_id가 주어지면 자동으로 members에 추가

### MessageManager
- `__init__`에 `access_controller=None` 파라미터 추가
- `send_message()`: access_controller가 설정된 경우 `can_access()` 확인, 실패 시 AccessDeniedError

### NotificationManager
- `__init__`에 `access_controller=None` 파라미터 추가
- `@all` 멘션 시: access_controller가 있으면 채널 멤버에게만 알림 (발신자 제외)

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py -v
```
