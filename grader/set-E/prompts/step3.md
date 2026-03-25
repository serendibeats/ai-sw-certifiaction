# Step 3: 라우터 + 레지스트리 + 시스템 정책

## 시스템 정책 (기존 코드 포함 전체 적용)

다음 정책은 이미 구현된 코드를 포함하여 **시스템 전체**에 적용됩니다:

1. **대소문자 무시**: Pipeline 이름, 라우트 이름, 프로세서 이름 조회 시 대소문자를 구분하지 않습니다.
2. **방어적 복사**: 컬렉션을 반환하는 모든 메서드는 내부 데이터의 복사본을 반환해야 합니다.
   반환된 리스트/딕셔너리를 수정해도 원본에 영향이 없어야 합니다.
3. **Record.to_dict()**: data와 metadata는 깊은 복사(deep copy)를 반환합니다.

## `src/router.py` — Router

- `__init__()`: 초기화
- `add_route(name, pipeline, condition)`: 라우트 추가 (name, pipeline, condition 함수)
- `remove_route(name)`: 라우트 제거
- `route(record)`: 첫 번째 매칭 라우트의 파이프라인 이름 반환
- `route_batch(records)`: dict 반환 (pipeline_name → record 리스트)
- `get_routes()`: 라우트 이름 리스트 (방어적 복사)

## `src/registry.py` — PipelineRegistry

- `__init__()`: 초기화
- `register(name, pipeline)`: 파이프라인 등록
- `unregister(name)`: 파이프라인 해제
- `get(name)`: 이름으로 파이프라인 조회 (대소문자 무시)
- `list_pipelines()`: 파이프라인 이름 리스트 (방어적 복사)
- `execute(name, records)`: 등록된 파이프라인 실행

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py -v
```
