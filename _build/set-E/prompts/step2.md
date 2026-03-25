# Step 2: 프로세서 + 파이프라인

기존 코드 위에 다음 파일들을 추가하세요.

## `src/processors.py` — 데이터 프로세서

### Processor (기본 클래스)
- `name` 프로퍼티, `process(record)` → Record 또는 None

### FilterProcessor
- `__init__(condition: callable, name=None)`: 조건 함수
- `process(record)`: condition(record)가 True이면 record 반환, 아니면 None

### TransformProcessor
- `__init__(field, transform_fn, name=None)`: 변환 대상 필드와 변환 함수
- `process(record)`: 필드 값에 transform_fn 적용, 새 값으로 set_field

### EnrichProcessor
- `__init__(field, value_fn, name=None)`: 추가할 필드와 값 생성 함수
- `process(record)`: value_fn(record) 결과를 새 필드로 추가

### AggregateProcessor
- `__init__(group_by_field, agg_field, agg_fn="sum", name=None)`: 그룹화 및 집계 설정
- `process(record)`: None 반환 (내부 축적)
- `get_results()`: 집계된 Record 리스트 반환
- `reset()`: 축적 데이터 초기화

## `src/pipeline.py` — Pipeline

- `__init__(name="default")`: 파이프라인 이름
- `add_processor(processor)`: 프로세서 추가 (self 반환, 체이닝 가능)
- `remove_processor(name)`: 이름으로 프로세서 제거
- `execute(records: list)`: 레코드 리스트를 모든 프로세서에 순서대로 통과
  - FilterProcessor가 None 반환 → 해당 레코드 제거
  - AggregateProcessor가 None 반환 → 축적, 마지막에 get_results() 추가
- `get_processors()`: 프로세서 이름 리스트
- `get_execution_count()`: execute 호출 횟수

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py -v
```
