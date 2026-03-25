# Step 6: 에러 복구 — Dead Letter Queue

## `src/dead_letter.py` — DeadLetterQueue

### DLQEntry
- `id` (UUID), `record`, `error` (str), `processor_name` (str), `timestamp`

### DeadLetterQueue
- `__init__(max_size=1000)`: 최대 크기 설정
- `add(record, error, processor_name=None)`: 실패 레코드 추가
- `get_all()`: 모든 항목 (방어적 복사)
- `get_by_processor(processor_name)`: 프로세서별 조회
- `retry(entry_id)`: DLQ에서 제거 후 레코드 반환 (재처리용)
- `clear()`: 모든 항목 삭제
- `count`: 항목 수 (프로퍼티)

## Pipeline 소급 수정

- `Pipeline.__init__`에 `dead_letter_queue` 옵션 파라미터 추가
- DLQ가 설정된 경우: 프로세서가 예외 발생 시 catch하여 DLQ에 추가, 나머지 레코드 계속 처리
- DLQ가 없는 경우: 기존 fail-fast 동작 유지 (예외 즉시 전파)

## Router 소급 수정

- `Router.__init__`에 `dead_letter_queue` 옵션 파라미터 추가
- 매칭 라우트가 없으면 DLQ에 추가 (RouterError 대신)

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py tests/test_step6.py -v
```
