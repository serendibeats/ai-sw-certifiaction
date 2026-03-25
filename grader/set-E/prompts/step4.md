# Step 4: 스키마 레지스트리 + 마이그레이션

## `src/schema_registry.py` — SchemaRegistry + SchemaMigrator

### SchemaRegistry
- `__init__()`: 초기화
- `register(schema)`: 스키마 등록 (name + version으로 저장)
- `get(name, version=None)`: 이름과 버전으로 조회 (version이 None이면 최신 버전)
- `get_versions(name)`: 버전 번호 리스트
- `list_schemas()`: 스키마 이름 리스트

### SchemaMigrator
- `__init__(schema_registry)`: SchemaRegistry 참조 저장
- `migrate(record, target_schema)`: 레코드를 대상 스키마로 마이그레이션
  - 누락 필드에 대상 스키마의 기본값 추가
  - 레코드에 있지만 대상에 없는 필드는 유지 (전방 호환)
  - record.schema를 target_schema로 갱신
  - 새 Record 반환 (원본 불변)

## 프로세서 내구성 강화

모든 프로세서는 스키마 v1의 레코드(일부 필드 누락)를 처리할 수 있어야 합니다:
- `TransformProcessor`: 필드가 없으면 건너뛰기 (오류 아님)
- `EnrichProcessor`: 소스 필드가 없으면 기본값 사용
- `FilterProcessor`: 조건 필드가 없으면 매칭 안 됨 처리

## Pipeline 확장

- `__init__`에 `schema_registry` 옵션 파라미터 추가
- `target_schema` 설정 시, 처리 전 자동 마이그레이션 수행

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py -v
```
