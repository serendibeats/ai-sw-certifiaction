# Step 1: 데이터 레코드 기반 시스템

다음 파일들을 `src/` 아래에 구현하세요.

## `src/errors.py` — 커스텀 예외 클래스

- `PipelineError(message)`: 파이프라인 기본 예외
- `RecordValidationError(record_id, errors)`: 레코드 검증 실패
- `SchemaError(message)`: 스키마 관련 오류
- `ProcessorError(processor_name, record_id, message)`: 프로세서 처리 오류
- `RouterError(record_id, message)`: 라우팅 실패
- `SerializationError(message)`: 직렬화/역직렬화 오류
- `InvalidRecordError(message)`: 유효하지 않은 레코드
- `DuplicateRecordError(record_id)`: 중복 레코드

각 예외는 관련 정보를 속성으로 저장하고, 적절한 메시지를 가져야 합니다.

## `src/record.py` — Record + Schema 모델

### RecordStatus (Enum)
- `RAW`, `VALIDATED`, `PROCESSED`, `ENRICHED`, `FAILED`, `ARCHIVED`

### Schema
- `name` (str), `version` (int, 기본값 1), `fields` (dict, 기본값 빈 딕셔너리)
  - fields는 `field_name → {"type": str, "required": bool, "default": any}` 매핑
- `validate(data)`: 데이터 검증, 오류 문자열 리스트 반환
- `get_required_fields()`: 필수 필드 이름 리스트
- `has_field(name)`: 필드 존재 여부 (bool)
- `to_dict()`: 딕셔너리 변환
- `__eq__`, `__hash__`: name + version 기준

### Record
- `id` (str, 자동 UUID), `data` (dict), `schema` (Schema, optional)
- `status` (RecordStatus, 기본값 RAW)
- `created_at`, `updated_at` (자동 설정, `time.time()`)
- `metadata` (dict, 기본값 빈 딕셔너리)
- `source` (str, 기본값 ""), `errors` (list, 기본값 빈 리스트)
- `get_field(name, default=None)`: 데이터 필드 조회
- `set_field(name, value)`: 데이터 필드 설정, `updated_at` 갱신
- `validate()`: 스키마 기준 검증, 오류 리스트 반환
- `is_valid()`: 검증 통과 여부 (bool)
- `to_dict()`: 딕셔너리 변환 (data, metadata는 깊은 복사)

## `src/validators.py` — 검증기

### Validator (기본 클래스)
- `name` 프로퍼티, `validate(record)` → 오류 리스트

### RequiredFieldValidator
- `__init__(fields: list)`: 필수 필드 목록
- `validate(record)`: 필드 존재 및 None 여부 확인

### TypeValidator
- `__init__(field, expected_type)`: 필드와 기대 타입
- `validate(record)`: 타입 확인

### RangeValidator
- `__init__(field, min_val=None, max_val=None)`: 숫자 범위
- `validate(record)`: 범위 확인

### CompositeValidator
- `__init__(validators: list)`: 검증기 목록
- `validate(record)`: 모든 검증기 실행, 오류 통합

## `src/serializer.py` — RecordSerializer

- `serialize(record)`: Record → dict (전체 직렬화)
- `deserialize(data, schema=None)`: dict → Record
- `serialize_batch(records)`: 리스트 직렬화
- `deserialize_batch(data_list, schema=None)`: 리스트 역직렬화

## 검증

```bash
pytest tests/test_step1.py -v
```
