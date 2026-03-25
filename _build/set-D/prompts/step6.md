# Step 6: 엔터티 관계 + 캐스케이드 삭제

## 시스템 정책 (계속 적용)
1. 모든 문자열 검색/비교는 대소문자를 구분하지 않습니다.
2. 컬렉션 반환 시 방어적 복사를 합니다.

## `src/relations.py` — RelationManager

### __init__(self, task_manager, project_manager)

### 의존성 관리
- `add_dependency(task_id, depends_on_task_id)`: 태스크 의존성 추가
  - 추가 전 순환 의존성 검사. 순환이면 `CircularDependencyError`
- `remove_dependency(task_id, depends_on_task_id)`: 의존성 제거
- `get_dependencies(task_id)` → list: 의존하는 태스크 ID 리스트
- `get_dependents(task_id)` → list: 이 태스크에 의존하는 태스크 ID 리스트 (역방향)
- `has_circular_dependency(task_id, depends_on_task_id)` → bool: 순환 의존성 여부

### 댓글 관리
- `add_comment(entity_type, entity_id, user_id, content)` → dict: 댓글 추가
- `get_comments(entity_type, entity_id)` → list: 댓글 리스트
- `remove_comments_for_entity(entity_type, entity_id)`: 엔터티의 모든 댓글 제거

## 캐스케이드 삭제

### TaskManager
- `_remove_task_internal`: 태스크 삭제 시 관련 댓글 및 의존성도 정리
- `__init__`에 `relation_manager=None` 파라미터 추가

### ProjectManager
- `_remove_project_internal`: 프로젝트 삭제 시 **해당 프로젝트의 모든 태스크를 먼저 삭제** (캐스케이드)
  - 각 태스크의 댓글과 의존성도 함께 정리
  - 프로젝트 자체의 댓글도 정리
- `__init__`에 `relation_manager=None`, `task_manager=None` 파라미터 추가

### DeleteProjectCommand 수정
- `execute()` 전에 캐스케이드될 모든 엔터티(태스크, 댓글, 의존성)를 저장
- `undo()` 시 저장된 모든 엔터티(프로젝트 + 태스크 + 댓글 + 의존성)를 복원

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py tests/test_step6.py -v
```
