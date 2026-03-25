# Step 1: 태스크/프로젝트/사용자 관리 기초

다음 파일들을 `src/` 아래에 구현하세요.

## `src/exceptions.py` — 커스텀 예외 클래스

- `TaskNotFoundError(task_id)`: 태스크 미발견
- `ProjectNotFoundError(project_id)`: 프로젝트 미발견
- `UserNotFoundError(user_id)`: 사용자 미발견
- `DuplicateTaskError(task_id)`: 중복 태스크
- `DuplicateProjectError(project_id)`: 중복 프로젝트
- `DuplicateUserError(user_id)`: 중복 사용자
- `InvalidTaskError(message)`: 유효하지 않은 태스크 데이터
- `InvalidProjectError(message)`: 유효하지 않은 프로젝트 데이터
- `InvalidUserError(message)`: 유효하지 않은 사용자 데이터
- `PermissionDeniedError(user_id, action)`: 권한 없음
- `InvalidTransitionError(current_status, new_status)`: 유효하지 않은 상태 전이
- `CircularDependencyError(task_id, depends_on_id)`: 순환 의존성

각 예외는 관련 정보를 속성으로 저장하고, 적절한 메시지를 가져야 합니다.

## `src/models.py` — 데이터 모델

### TaskStatus (Enum)
- `TODO`, `IN_PROGRESS`, `IN_REVIEW`, `DONE`, `CANCELLED`

### TaskPriority (Enum)
- `LOW(1)`, `MEDIUM(2)`, `HIGH(3)`, `CRITICAL(4)` — 숫자가 클수록 높은 우선순위

### Task
- 생성자: `id=None` (None이면 자동 UUID 생성), `title`, `description=""` 등
- `id` (str), `title` (str), `description` (str, 기본값 "")
- `status` (TaskStatus, 기본값 TODO)
- `priority` (TaskPriority, 기본값 MEDIUM)
- `project_id` (str, optional), `assignee_id` (str, optional)
- `tags` (list of str, 기본값 빈 리스트)
- `created_at` (float, 자동 설정 via `time.time()`)
- `updated_at` (float, 자동 설정)
- `metadata` (dict, 기본값 빈 딕셔너리)
- `story_points` (int, 기본값 0)
- **속성 컨벤션**: 가변 필드(tags, metadata)는 내부적으로 `self._tags`, `self._metadata`에 저장하고, `@property`로 방어적 복사본을 반환합니다. setter는 값을 복사하여 저장합니다.
- `transition_to(new_status)` → `True`: 유효한 상태 전이 수행 후 `True`를 반환. 유효하지 않으면 `InvalidTransitionError`.
  - 유효한 전이: TODO→IN_PROGRESS, IN_PROGRESS→IN_REVIEW/TODO, IN_REVIEW→DONE/IN_PROGRESS, 어디서든→CANCELLED (DONE에서도 CANCELLED로 전이 가능)
  - CANCELLED만 최종 상태 (전이 불가)
- `update(**kwargs)`: 전달된 필드만 변경, `updated_at` 자동 갱신
- `to_dict()`: 모든 필드를 딕셔너리로 변환 (status, priority는 문자열로). tags와 metadata는 깊은 복사본 반환.
- `__eq__`, `__hash__`: id 기준

### ProjectStatus (Enum)
- `ACTIVE`, `ON_HOLD`, `COMPLETED`, `ARCHIVED`

### Project
- 생성자: `id=None` (None이면 자동 UUID 생성), `name`, `description=""` 등
- `id` (str), `name` (str), `description` (str, 기본값 "")
- `owner_id` (str, optional)
- `status` (ProjectStatus, 기본값 ACTIVE)
- `created_at`, `updated_at` (자동 설정)
- `metadata` (dict, 기본값 빈 딕셔너리) — Task와 동일하게 `self._metadata` + `@property` 방어적 복사
- `update(**kwargs)`, `to_dict()`, `__eq__`, `__hash__`

### User
- 생성자: `id=None` (None이면 자동 UUID 생성), `username`, `email` 등
- `id` (str), `username` (str), `email` (str)
- `role` (str, 기본값 "member"). 유효 역할: "admin", "manager", "member", "viewer"
- `created_at` (자동 설정)
- `to_dict()`, `__eq__`, `__hash__`

## `src/task_manager.py` — TaskManager

내부적으로 `{id: Task}` 딕셔너리로 저장합니다.

- `add_task(title, description="", priority=MEDIUM, project_id=None, assignee_id=None, tags=None, story_points=0, metadata=None)` → Task
  - UUID를 자동 생성하여 id로 사용
- `get_task(task_id)` → Task. 없으면 `TaskNotFoundError`
- `update_task(task_id, **kwargs)` → Task
- `remove_task(task_id)`
- `list_tasks()` → list
- `get_tasks_by_project(project_id)` → list
- `get_tasks_by_assignee(assignee_id)` → list
- `get_tasks_by_status(status)` → list
- `get_tasks_by_priority(priority)` → list
- `search_tasks(query)` → list (title + description에서 검색)
- `count` → property

## `src/project_manager.py` — ProjectManager

- `add_project(name, description="", owner_id=None)` → Project
- `get_project(project_id)` → Project
- `update_project(project_id, **kwargs)` → Project
- `remove_project(project_id)`
- `list_projects()` → list
- `search_projects(query)` → list
- `count` → property

## `src/user_manager.py` — UserManager

- `add_user(username, email, role="member")` → User
- `get_user(user_id)` → User
- `get_user_by_username(username)` → User
- `update_user(user_id, **kwargs)` → User
- `remove_user(user_id)`
- `list_users()` → list
- `count` → property

## 검증

```bash
pytest tests/test_step1.py -v
```
