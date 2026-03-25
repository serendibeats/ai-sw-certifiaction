# Step 4: 훅 파이프라인 (미들웨어)

## 시스템 정책 (계속 적용)
1. 모든 문자열 검색/비교는 대소문자를 구분하지 않습니다.
2. 컬렉션 반환 시 방어적 복사를 합니다.

## `src/hooks.py` — 훅 시스템

### HookContext
- `action` (str): 실행 중인 액션
- `entity_type` (str): 엔터티 타입 ("task", "project", "user")
- `entity_id` (str): 엔터티 ID
- `data` (dict): 액션 데이터
- `user_id` (str|None): 실행한 사용자 ID
- `timestamp` (float): 발생 시각 (자동 설정)
- `result` (any): 액션 결과

### Hook (베이스 클래스)
- `name` → property: 훅 이름
- `before(context)` → context: 액션 전 호출
- `after(context)` → context: 액션 후 호출

### AuditLogHook(Hook)
- 모든 mutation을 내부 리스트에 기록
- `before()`: "before" 단계 로그 기록
- `after()`: "after" 단계 로그 기록
- 로그 엔트리 형식 (정확한 키 이름):
  ```python
  {"action": action, "entity_type": entity_type, "entity_id": entity_id,
   "phase": "before"/"after", "timestamp": timestamp, "user_id": user_id}
  ```
  **주의: `"phase"` 키를 사용합니다 (`"stage"`가 아님).**
- `get_audit_log()` → list (방어적 복사본)
- `clear()` → 로그 초기화

### ValidationHook(Hook)
- `before()`에서 데이터 유효성 검증
  - create_task/update_task: title이 비어있으면 `InvalidTaskError`
  - create_project/update_project: name이 비어있으면 `InvalidProjectError`
  - create_user/update_user: username이 비어있으면 `InvalidUserError`

### HookPipeline
- `register(hook)`: 훅 등록
- `unregister(hook_name)`: 훅 제거
- `execute_before(context)` → context: 모든 훅의 before를 순서대로 실행
- `execute_after(context)` → context: 모든 훅의 after를 순서대로 실행
- `get_hooks()` → list: 등록된 훅 이름 리스트

## 기존 매니저에 훅 파이프라인 추가

### TaskManager
- `__init__`에 `hook_pipeline=None` 파라미터 추가
- 모든 mutation (`add_task`, `update_task`, `remove_task`)을 훅으로 감싸기:
  1. HookContext 생성
  2. `pipeline.execute_before(context)`
  3. 권한 검사
  4. 실제 액션 수행
  5. `pipeline.execute_after(context)`

### ProjectManager, UserManager
- 동일한 패턴으로 훅 파이프라인 추가

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py -v
```
