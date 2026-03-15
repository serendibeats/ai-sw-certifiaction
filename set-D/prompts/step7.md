# Step 7: 계산 프로퍼티 + 분석 엔진

## 시스템 정책 (계속 적용)
1. 모든 문자열 검색/비교는 대소문자를 구분하지 않습니다.
2. 컬렉션 반환 시 방어적 복사를 합니다.

## Task.story_points — 계산 프로퍼티로 변경

기존에 직접 필드였던 `story_points`를 **계산 프로퍼티**로 마이그레이션합니다:

- `metadata.get("complexity")`에 기반한 자동 계산:
  - `"trivial"` → 1, `"simple"` → 2, `"medium"` → 3, `"complex"` → 5, `"epic"` → 8
- `_metadata`에 명시적 `"story_points"` 키가 있으면 해당 값 우선 사용
- 기본값(complexity 미설정 시): `"medium"` → 3
- `story_points` 세터: `_metadata["story_points"]`에 값 저장
- **하위 호환성**: 생성자에서 `story_points=N`으로 직접 설정해도 동작

## Project.progress — 계산 프로퍼티

- `task_manager` 참조를 통해 해당 프로젝트의 DONE 태스크 비율 계산
- `task_manager`가 None이면 0.0 반환
- 태스크가 없으면 0.0 반환

## Project.health — 계산 프로퍼티

- progress >= 0.7: `"healthy"`
- progress >= 0.3: `"at_risk"`
- progress < 0.3: `"critical"`
- `task_manager`가 None이면 `"unknown"` 반환

Project에 `task_manager` optional 파라미터를 추가하세요. ProjectManager에서 프로젝트 생성 시 `task_manager`를 전달합니다.

## Project.to_dict() 확장

`to_dict()` 결과에 계산 프로퍼티를 포함합니다:
- `"progress"`: `self.progress` 값
- `"health"`: `self.health` 값

## `src/analytics.py` — AnalyticsEngine

- `__init__(self, task_manager, project_manager, user_manager=None)`
- `get_velocity(project_id, days=7)` → dict
  - `completed_points`: 기간 내 완료된 스토리 포인트 합
  - `completed_count`: 기간 내 완료된 태스크 수
- `get_workload_distribution()` → dict: user_id → 태스크 수
- `get_project_summary(project_id)` → dict
  - `name`, `progress`, `health`, `total_tasks`, `by_status` — `by_status`의 키는 상태 이름 문자열 (예: `"TODO"`, `"DONE"`)
- `get_team_report(project_id)` → dict
  - `members`: user_id → `{assigned, completed, in_progress}`
- `get_burndown_data(project_id)` → list of dicts

## 완료 태스크 추적

TaskManager에 완료 태스크 스냅샷 기능을 추가합니다:
- `_record_completion(task)`: 태스크가 DONE이면 `to_dict()` 스냅샷을 저장하는 메서드
- `_track_completion(task)`: `_record_completion`과 동일 기능 (내부 호출용)
- 태스크가 DONE으로 전이될 때 자동으로 스냅샷 저장 (Board.move_task, update_task 등 모든 경로에서)
- `get_completed_tasks()` → list: 완료된 태스크 스냅샷 리스트 (방어적 복사)

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py tests/test_step6.py tests/test_step7.py -v
```
