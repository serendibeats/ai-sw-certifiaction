# Step 8: 검증 강화 + 리포트 + 체인 검증

## 검증 강화 (소급 수정)

- `CompositeValidator`에 `strict` 모드 추가: True이면 스키마에 없는 필드도 오류
- `Pipeline`에 validators 설정 시 처리 전 레코드 검증 수행

## `src/reports.py` — ReportGenerator

- `__init__(metrics_collector=None, dead_letter_queue=None)`: 옵션 의존성 주입
- `pipeline_report(pipeline_name)`: dict 반환
  - `execution_count`, `total_records`, `success_rate`, `avg_duration`
- `dlq_report()`: dict 반환
  - `total`, `by_processor` (프로세서별 분류), `oldest_entry`, `newest_entry`
- `processor_performance_report()`: dict 반환
  - 프로세서별 메트릭, `avg_duration` 기준 정렬

## Pipeline 확장

- `_executions` dict: 실행 이력 저장 (execution_id → {timestamp, record_count, success_count, fail_count, duration_ms})
- `get_execution_history()`: 실행 이력 리스트 (방어적 복사)
- `get_last_execution()`: 마지막 실행 정보 또는 None

## 프로세서 체인 검증

- `Pipeline.validate_chain()`: 경고 리스트 반환
  - FilterProcessor 다음에 AggregateProcessor가 있으면 경고
  - TransformProcessor 출력 필드가 다음 프로세서 입력에 맞는지 확인
  - 경고는 참고용 (오류가 아님)

## 검증

```bash
pytest tests/ -v
```
