# Step 6: 전문 검색 인덱스

## `src/search_index.py` — SearchIndex

역 인덱스 기반 전문 검색 엔진을 구현합니다.

### SearchIndex
- `__init__(self)`: 내부 인덱스 초기화
- `index_message(message)`: 메시지 내용을 토큰화하여 인덱싱
  - 토큰화: 소문자 변환, 공백 분리, 구두점 제거
- `remove_message(message_id)`: 인덱스에서 제거
- `update_message(message)`: 기존 항목 제거 후 재인덱싱
- `search(query, limit=50)` → list of message_ids
  - 대소문자 구분 없는 검색
  - 쿼리 용어 일치 수로 점수 매기기 (높은 점수 우선)
- `get_index_size()` → int: 인덱싱된 메시지 수
- `get_unique_terms()` → int: 고유 용어 수
- `get_top_terms(n=10)` → list of (term, count) tuples
- `rebuild(messages)`: 전체 재인덱싱

## 기존 코드 수정 — Cross-Cutting 동기화

모든 메시지 mutation에서 검색 인덱스를 동기화해야 합니다:

### MessageManager
- `__init__`에 `search_index=None` 추가
- `send_message()`: search_index가 설정되면 새 메시지 인덱싱
- `edit_message()`: search_index가 설정되면 인덱스 업데이트
- `delete_message()` (소프트 삭제): search_index가 설정되면 인덱스에서 제거
- `search_messages()`: search_index가 있으면 인덱스 사용, 없으면 선형 검색 폴백

### ThreadManager
- `reply()`: message_manager의 search_index가 설정되면 답글도 인덱싱

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py tests/test_step6.py -v
```
