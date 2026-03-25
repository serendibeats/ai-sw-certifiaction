# Step 5: Undo/Redo 스택 (Command 패턴)

## 시스템 정책 (계속 적용)
1. 모든 문자열 검색/비교는 대소문자를 구분하지 않습니다.
2. 컬렉션 반환 시 방어적 복사를 합니다.

## `src/history.py` — Command 패턴 + HistoryManager

### Command (베이스 클래스)
- `execute()` → any: 커맨드 실행
- `undo()` → any: 실행 취소
- `description` → property: 커맨드 설명 — **클래스 이름 스타일 사용** (예: `"CreateTask: ..."`, `"UpdateTask: ..."`, `"DeleteTask: ..."`)

### CreateTaskCommand(Command)
- `__init__(task_manager, title, description, priority, project_id, assignee_id, tags, story_points, user_id)`
- `execute()`: 태스크 생성
- `undo()`: 생성된 태스크 삭제
- `description`: `"CreateTask: {title}"`

### UpdateTaskCommand(Command)
- 실행 전 이전 상태를 저장하고, undo 시 복원
- `description`: `"UpdateTask: {task_id}"`

### DeleteTaskCommand(Command)
- 삭제된 태스크를 저장하고, undo 시 복원
- `description`: `"DeleteTask: {task_id}"`

### CreateProjectCommand, UpdateProjectCommand, DeleteProjectCommand
- 태스크 커맨드와 동일한 패턴
- description도 동일 패턴: `"CreateProject: ..."`, `"UpdateProject: ..."`, `"DeleteProject: ..."`

### HistoryManager
- `__init__(self, max_size=100)`
- `execute(command)` → result: 커맨드 실행 후 undo 스택에 추가
- `undo()` → result: undo 스택에서 꺼내 실행 취소, redo 스택에 추가
- `redo()` → result: redo 스택에서 꺼내 재실행, undo 스택에 추가
- `can_undo` → bool
- `can_redo` → bool
- `get_history()` → list: 커맨드 설명 리스트

## 매니저에 내부 메서드 분리

기존 공개 메서드에서 **실제 로직**을 내부 메서드로 분리합니다:

### TaskManager
- `_add_task_internal(title, ...)` → Task: 훅/권한 없이 태스크 추가
- `_update_task_internal(task_id, **kwargs)` → Task
- `_remove_task_internal(task_id)` → Task (삭제된 태스크 반환)
- 공개 메서드(`add_task` 등)는 훅 → 권한 → 내부 메서드 순으로 호출

### ProjectManager
- `_add_project_internal`, `_update_project_internal`, `_remove_project_internal`
- ProjectManager와 UserManager도 동일한 `_internal` 패턴 적용

**중요**: Command의 `execute()`와 `undo()`는 **내부 메서드**를 호출해야 합니다.
공개 메서드를 호출하면 훅과 권한 검사가 중복 실행됩니다.

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py -v
```
