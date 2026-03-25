# 순차적 개발 시험: 전자상거래 시스템

## 개요

8단계 순차 프롬프트로 AI 코딩 에이전트에게 전자상거래 시스템을 구축하게 한 뒤,
통합 테스트(test_final.py)로 구조적 코드 품질을 검증합니다.

- **도메인**: 장바구니 → 주문 → 할인 → 환불 흐름의 전자상거래
- **평가**: 단계별 테스트(test_step1~8) + 통합 테스트(test_final, 등급용)

## 테스트 현황

- 레퍼런스 구현: 16 files, 1,056 lines
- 전체 테스트: 173개 (test_final: 66개)
- 레퍼런스 통과율: 173/173 (100%)

---

## 단계별 설계

| Step | 주제 | 핵심 함정 |
|------|------|----------|
| 1 | 카탈로그 + 재고 기반 | — |
| 2 | 장바구니 + 가격 계산 | — |
| 3 | 주문 + 시스템 정책 | weight 필드 소급 추가, 대소문자 무시/방어적 복사 |
| 4 | 이벤트 시스템 | EventBus cross-cutting, 이벤트 데이터 불변성 |
| 5 | 할인 + 재고 예약 전환 | 직접 차감 → 예약/확인 패턴 |
| 6 | 리뷰 + 위시리스트 | 리뷰 기반 정렬, 카탈로그 연동 |
| 7 | 쿠폰 + 주문 환불 | 환불 금액 검증, 재고 복원 |
| 8 | 데이터 검증 + 보고서 | 검증 규칙 소급 적용 |

### 단계별 상세 요약

- **Step 1**: `exceptions`, `models`, `catalog`, `inventory`, `serializer` — Product/Category CRUD, 재고 관리, 직렬화.
- **Step 2**: `cart`, `pricing` — CartItem/ShoppingCart, 카탈로그 연동, 소계/배송비 계산.
- **Step 3**: `order`, `order_service` — Order/OrderLine, 상태 전이, **전체 정책**(대소문자 무시, 방어적 복사), Product에 `weight` 소급 추가.
- **Step 4**: `events` — EventBus, subscribe/publish, **기존 4개 클래스에 이벤트 주입**, 이벤트 데이터는 복사본으로 저장.
- **Step 5**: `discounts` — 할인 엔진, **재고 직접 차감 → 예약/확인 패턴**으로 전환.
- **Step 6**: `reviews`, `wishlist` — 리뷰/평점, 위시리스트, **카탈로그에 review_manager 연동**, 리뷰 기반 정렬.
- **Step 7**: `coupons` — 쿠폰 적용, **환불 금액 검증** 및 **재고 복원**.
- **Step 8**: `reports` + 검증 강화 — add_product/update_product에 **검증 규칙 소급 적용**, ReportGenerator.

---

## 진행 순서

| 순서 | 내용 |
|------|------|
| 1 | **Step 1 → Step 8**까지 **한 번에 하나씩** `prompts/stepN.md`만 보고 구현 |
| 2 | 각 단계 구현 후 **해당 단계 테스트** 실행: `pytest tests/test_stepN.py -v` |
| 3 | 8단계까지 끝나면 **전체 테스트**와 **통합 테스트**로 최종 채점 |

프롬프트는 반드시 순서대로만 제공하고, 한 단계가 통과한 뒤 다음 단계로 넘어가는 것을 권장합니다.

---

## 진행 방법 (환경·명령어)

### 환경 요구사항

- Python 3.9+
- pytest (`pip install pytest`)

### 저장소 기준 이동

```bash
cd grader-C
```

### 처음부터 풀 때 (선택)

`src/`를 비우고 Step 1부터 구현할 때만 실행. `__init__.py`는 비우지 않습니다.

```bash
cd src && for f in *.py; do [ "$f" != "__init__.py" ] && echo "" > "$f"; done && cd ..
```

### 단계별 검증 (N = 1 ~ 8)

각 단계 구현 후 해당 테스트만 실행해 통과 여부를 확인합니다.

```bash
python3 -m pytest tests/test_step1.py -v
python3 -m pytest tests/test_step2.py -v
python3 -m pytest tests/test_step3.py -v
python3 -m pytest tests/test_step4.py -v
python3 -m pytest tests/test_step5.py -v
python3 -m pytest tests/test_step6.py -v
python3 -m pytest tests/test_step7.py -v
python3 -m pytest tests/test_step8.py -v
```

### 최종 채점

8단계까지 끝난 뒤 전체·통합 테스트로 최종 점수를 냅니다.

```bash
python3 -m pytest tests/ -v                   # 전체 173개
python3 -m pytest tests/test_final.py -v       # 핵심 66개 (등급용)
```

- **전체**: step1~8 + test_final 포함 모든 테스트.
- **test_final**: 구조적 품질 핵심 지표(등급 A~F는 이 통과율 기준).

---

## 시험 규칙

- **순서 엄수**: step1 → step2 → … → step8 순서대로만 진행. 건너뛰거나 한꺼번에 주지 않습니다.
- **테스트 미공개**: 각 step을 풀 때 해당 step의 **테스트 파일은 보지 않고** `prompts/stepN.md` 요구사항만 보고 구현합니다. 테스트를 보면 구조적 품질이 아닌 테스트 맞춤이 되어 평가가 무의미해집니다.
- **한 세션에서**: 가능하면 같은 대화/세션에서 step1~8을 이어서 진행해 컨텍스트를 유지합니다. 이전 단계 코드 수정은 허용됩니다(시험의 핵심).

---

## 진행 선택지

- **처음부터 풀기**: `src/` 초기화 후 Step 1부터 순서대로 구현. 각 step 완료 시 `test_stepN.py`로 검증.
- **이미 구현된 코드가 있을 때**: 실패하는 step이 있으면 해당 step의 `stepN.md`와 기존 코드를 기준으로 수정. 이전 단계 코드 수정 가능.
- **현재 상태만 확인**: `pytest tests/ -v`와 `pytest tests/test_final.py -v` 실행 후 통과/실패를 보고, 어떤 step을 손봐야 할지 결정.

---

상세 가이드: [docs/EXAM_GUIDE.md](../docs/EXAM_GUIDE.md)
