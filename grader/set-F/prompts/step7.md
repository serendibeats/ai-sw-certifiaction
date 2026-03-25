# Step 7: 암호화 + 감사 로그

## `src/encryption.py` — EncryptionManager

간단한 XOR + Base64 암호화를 구현합니다.

### EncryptionManager
- `__init__(self, key: str)`: 빈 키는 EncryptionError
- `encrypt(plaintext)` → str: XOR + Base64 인코딩, "ENC:" 접두사 추가
- `decrypt(ciphertext)` → str: "ENC:" 접두사 확인 후 복호화
- `is_encrypted(text)` → bool: "ENC:" 접두사 여부 확인

### 하위 호환성
- "ENC:" 접두사가 없는 텍스트는 평문으로 취급 (복호화하지 않음)
- 빈 문자열은 그대로 반환

## `src/audit.py` — AuditLogger

### AuditEntry 모델 (models.py에 추가)
- `id` (UUID), `action`, `entity_type`, `entity_id`
- `user_id` (optional), `details` (dict), `timestamp`

### AuditLogger
- `log(action, entity_type, entity_id, user_id=None, details=None)` → AuditEntry
- `get_log()` → list (방어적 복사)
- `get_log_by_entity(entity_type, entity_id)` → list
- `get_log_by_user(user_id)` → list
- `get_log_by_action(action)` → list
- `clear()`: 로그 초기화

## 기존 코드 수정

### MessageManager
- `__init__`에 `encryption_manager=None`, `audit_logger=None` 추가
- `send_message()`: 암호화 후 저장, 인덱스에는 평문 사용, 반환 시 복호화
- `get_message()`: 복호화하여 반환
- `get_messages()`: 모든 메시지 복호화
- `edit_message()`: 새 내용 암호화 저장, 인덱스 평문 업데이트
- 모든 mutation에 감사 로그 기록 (send, edit, delete)

### ChannelManager
- `__init__`에 `audit_logger=None` 추가
- create, update, delete 시 감사 로그 기록

### ThreadManager
- `reply()`: message_manager의 암호화/감사 연동

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py tests/test_step6.py tests/test_step7.py -v
```
