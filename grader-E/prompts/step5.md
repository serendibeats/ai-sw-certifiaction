# Step 5: Lazy/Streaming + 우선순위 라우팅

## Pipeline 변경 — Lazy 실행

- `Pipeline.execute()`는 이제 **Iterable** (리스트뿐 아니라 generator도)을 받습니다
- **generator를 반환**합니다 (lazy 평가)
- 모든 프로세서는 generator 입력을 처리해야 합니다
- `AggregateProcessor`: 입력을 소비(materialize)한 후 집계
- 새 메서드: `execute_eager(records)` → list 반환 (하위 호환용, 결과를 즉시 생성)

## Pipeline 속성 추가

- `lazy` 프로퍼티 (기본값 True)
- `execute()`: lazy가 True이면 generator 반환, False이면 list 반환

## Router 변경 — 우선순위

- `add_route(name, pipeline, condition, priority=0)`: priority 파라미터 추가
- 라우트는 priority 순(높은 것 먼저)으로 정렬하여 매칭
- `route()`: 가장 높은 priority의 매칭 라우트 반환
- `route_batch()`: 각 레코드에 대해 가장 높은 priority 매칭

## 검증

```bash
pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py tests/test_step4.py tests/test_step5.py -v
```
