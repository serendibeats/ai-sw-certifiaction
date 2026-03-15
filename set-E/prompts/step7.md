# Step 7: 메트릭 수집 + Record 불변성

## `src/metrics.py` — MetricsCollector

- `__init__()`: 초기화
- `record_processing(processor_name, duration_ms, success)`: 프로세서 실행 기록
- `get_processor_metrics(processor_name)`: dict (total, success, failed, avg_duration)
- `get_all_metrics()`: 전체 프로세서 메트릭 (processor_name → metrics)
- `get_pipeline_metrics(pipeline_name)`: dict (total_records, success, failed, duration)
- `record_pipeline_execution(pipeline_name, record_count, duration_ms, success_count, fail_count)`
- `reset()`: 모든 메트릭 초기화

## Record 불변성 (파괴적 변경)

- `Record.set_field(name, value)`가 이제 **새 Record를 반환**합니다 (copy-on-write)
- 원본 레코드는 변경되지 않습니다
- 모든 프로세서에서 set_field 사용 시 반환값을 캡처해야 합니다:
  - `TransformProcessor`: `record = record.set_field(field, new_value)`
  - `EnrichProcessor`: `record = record.set_field(field, value)`
- `Record.copy()`: 깊은 복사본 반환

## Pipeline 소급 수정

- `Pipeline.__init__`에 `metrics_collector` 옵션 파라미터 추가
- 각 프로세서 실행을 감싸서 시간 측정, 성공/실패 기록
- 전체 파이프라인 실행 메트릭 기록

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py tests/test_step6.py tests/test_step7.py -v
```
