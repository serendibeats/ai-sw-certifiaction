# Step 2: 칸반 보드 + 고급 필터링

기존 코드 위에 다음을 추가하세요.

## `src/board.py` — Board (칸반 보드)

- `__init__(self, task_manager, project_id=None)`: task_manager 참조를 저장합니다. project_id가 있으면 해당 프로젝트의 태스크만 관리합니다.
- `get_columns()` → dict: TaskStatus → 태스크 리스트 매핑
- `get_column(status)` → list: 특정 상태의 태스크 리스트
- `move_task(task_id, new_status)` → Task: `task.transition_to`를 사용하여 상태 이동
- `get_wip_count(status)` → int: 해당 상태의 태스크 수
- `set_wip_limit(status, limit)` → None: WIP 제한 설정
- `check_wip_limit(status)` → bool: `get_wip_count(status) < limit`이면 True (제한 이내), `get_wip_count(status) >= limit`이면 False (제한 초과). 제한이 설정되지 않은 상태는 항상 True.

## TaskManager 확장 — 고급 필터링

### filter_tasks(status=None, priority=None, assignee_id=None, project_id=None, tags=None) → list
- 모든 필터는 AND 조합
- tags 필터: 태스크가 지정된 **모든** 태그를 보유해야 함

### sort_tasks(tasks, key="created_at", reverse=False) → list
- 지원 키: `"created_at"`, `"updated_at"`, `"priority"`, `"title"`, `"story_points"`
- priority 정렬: 기본(reverse=False)일 때 CRITICAL(4) > HIGH(3) > MEDIUM(2) > LOW(1) 순 (높은 우선순위 먼저). reverse=True이면 LOW → CRITICAL 순.

### get_task_statistics() → dict
- `"total"`: 전체 태스크 수
- `"by_status"`: 상태별 태스크 수 — 키는 상태 이름 문자열 (예: `"TODO"`, `"IN_PROGRESS"`, `"DONE"`)
- `"by_priority"`: 우선순위별 태스크 수 — 키는 우선순위 이름 문자열 (예: `"LOW"`, `"MEDIUM"`, `"HIGH"`, `"CRITICAL"`)
- `"avg_story_points"`: 평균 스토리 포인트

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py -v
```
