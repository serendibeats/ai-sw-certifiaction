# Step 8: 메시지 검증 + 채널 통계 + 리포트

## 메시지 검증 (기존 코드 수정)

### MessageManager
- `send_message()`와 `edit_message()`에 내용 검증 추가:
  - 빈 문자열 또는 공백만 → InvalidMessageError
  - 최대 길이 10000자 초과 → InvalidMessageError
  - 금지어 필터 (configurable list): 차단하지 않고 metadata["warnings"]에 경고 추가
- `__init__`에 `forbidden_words=None` (list) 추가

## 채널 통계

### ChannelManager 확장
- `__init__`에 `message_manager=None` 추가
- `get_channel_stats(channel_id)` → dict:
  - `channel_id`, `name`, `member_count`
  - `message_count`: 삭제되지 않은 루트 메시지 수
  - `active_users`: 메시지를 보낸 사용자 목록
  - `last_activity`: 가장 최근 메시지 타임스탬프

## `src/reports.py` — ReportGenerator

- `__init__(self, channel_manager=None, message_manager=None, user_manager=None, search_index=None)`

### 리포트 메서드
- `channel_activity_report(channel_id)` → dict:
  - `total_messages`, `messages_per_day` (추정치), `top_posters`, `peak_hours`
- `user_activity_report(user_id)` → dict:
  - `messages_sent`, `channels_active`, `avg_message_length`
- `search_index_report()` → dict:
  - `total_indexed`, `unique_terms`, `top_terms`
- `system_report()` → dict:
  - `total_users`, `total_channels`, `total_messages`, `active_channels` (메시지가 있는 채널)

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py tests/test_step6.py tests/test_step7.py tests/test_step8.py -v
```

## 최종 검증

```bash
pytest tests/test_final.py -v
```
