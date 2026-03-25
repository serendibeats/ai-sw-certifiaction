# Step 3: 권한 시스템 + 시스템 정책

## 시스템 정책 (기존 코드 포함 전체 적용)

다음 정책은 이미 구현된 코드를 포함하여 **시스템 전체**에 적용됩니다:

1. **모든 문자열 검색/비교는 대소문자를 구분하지 않습니다.**
   - `search_tasks`, `search_projects`, `get_user_by_username` 등
   - `filter_tasks`의 tags 필터도 대소문자 무시
2. **컬렉션을 반환하는 모든 메서드는 내부 데이터의 복사본을 반환해야 합니다.**
   - `list_tasks()`, `list_projects()`, `list_users()` 등은 방어적 복사
   - `to_dict()`는 tags, metadata의 깊은 복사 포함
3. **가변 속성(tags, metadata)의 방어적 복사**: `@property`가 복사본을 반환하므로, 외부에서 반환값을 수정해도 내부 상태에 영향 없음.

## `src/permissions.py` — PermissionChecker

- `__init__(self, user_manager)`: UserManager 참조
- `check_permission(user_id, action, resource=None)` → bool
  - **user_id가 존재하지 않는 사용자이면 False를 반환** (예외를 발생시키지 않음)
  - **resource=None이면 일반 권한 검사 (소유권 확인 없음)**
  - 액션 목록: `"create_task"`, `"update_task"`, `"delete_task"`, `"create_project"`, `"update_project"`, `"delete_project"`, `"manage_users"`, `"view"`
  - admin: 모든 액션
  - manager: `manage_users`를 제외한 모든 액션 가능
  - member: `create_task`, `update_task`, `delete_task`, `view` (단, update/delete는 자기 태스크만)
  - viewer: `view`만
  - member의 자기 태스크 판별: `resource.assignee_id == user_id`
- `require_permission(user_id, action, resource=None)` → 권한 없으면 `PermissionDeniedError`

## 기존 매니저에 권한 시스템 추가

### TaskManager
- `__init__`에 `permission_checker=None` 파라미터 추가
- `add_task`, `update_task`, `remove_task`에 `user_id=None` 파라미터 추가
- `permission_checker`가 설정되고 `user_id`가 주어지면 액션 전에 권한 검사
- member의 `update_task`, `remove_task`: 자기 태스크(assignee_id == user_id)만 허용

### ProjectManager
- `__init__`에 `permission_checker=None` 파라미터 추가
- `add_project`, `update_project`, `remove_project`에 `user_id=None` 파라미터 추가

### UserManager
- `__init__`에 `permission_checker=None` 파라미터 추가
- `add_user`, `update_user`, `remove_user`에 관리자 `user_id` 파라미터 추가
- 사용자 관리 액션은 `manage_users` 권한 필요

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py -v
```
