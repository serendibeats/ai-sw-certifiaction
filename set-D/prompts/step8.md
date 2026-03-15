# Step 8: 유효성 검증 + 직렬화 + 보고서

## 시스템 정책 (계속 적용)
1. 모든 문자열 검색/비교는 대소문자를 구분하지 않습니다.
2. 컬렉션 반환 시 방어적 복사를 합니다.

## 데이터 유효성 검증 강화

### TaskManager
- 태스크 생성/수정 시 유효성 검증:
  - title은 비어있을 수 없음 → `InvalidTaskError`
  - priority는 유효한 `TaskPriority` 값이어야 함
  - story_points는 0 이상
- 내부 메서드(`_add_task_internal`, `_update_task_internal`)에서도 검증

### ProjectManager
- name은 비어있을 수 없음 → `InvalidProjectError`
- status는 유효한 `ProjectStatus` 값이어야 함

### UserManager
- username, email은 비어있을 수 없음 → `InvalidUserError`
- role은 유효한 역할이어야 함

## `src/serializer.py` — 직렬화/역직렬화

### TaskSerializer
- `serialize(task)` → dict: 계산 프로퍼티 포함
- `deserialize(data)` → Task
  - **하위 호환성**: 이전 포맷(직접 story_points)과 새 포맷(complexity 기반) 모두 지원
  - 이전 포맷: `{"story_points": 13, "metadata": {}}` → metadata에 story_points 저장
  - 새 포맷: `{"metadata": {"complexity": "epic"}}` → 자동 계산

### ProjectSerializer
- `serialize(project)` → dict
- `deserialize(data, task_manager=None)` → Project

### UserSerializer
- `serialize(user)` → dict
- `deserialize(data)` → User

## 완료 태스크 추적 (모든 경로)

완료 추적은 DONE으로의 **모든** 전이 경로에서 발생합니다:
- `update_task(task_id, status=TaskStatus.DONE)` — TaskManager.update_task 경로
- `Board.move_task(task_id, TaskStatus.DONE)` — Board 경로
- Command를 통한 상태 변경

## AnalyticsEngine 확장

- `get_team_report(project_id)` → dict
  - `project_id`, `members`: user_id별 `{assigned, completed, in_progress}` 통계
- `get_burndown_data(project_id)` → list
  - 일별 잔여 태스크 수 스냅샷

## 검증

```bash
pytest tests/ -v
```
