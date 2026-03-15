# AI 코딩 에이전트 구조적 코드 품질 평가 시험

## 목차

1. [시험 개요](#1-시험-개요)
2. [시험 설계 철학](#2-시험-설계-철학)
3. [시험 셋 구성](#3-시험-셋-구성)
4. [응시자 가이드](#4-응시자-가이드-ai-코딩-에이전트-운영자)
5. [시험관 가이드](#5-시험관-가이드-평가자)
6. [셋별 상세 설계](#6-셋별-상세-설계)
7. [스파게티 유도 패턴 분석](#7-스파게티-유도-패턴-분석)
8. [검증 결과 (내부용)](#8-검증-결과-내부용)
9. [채점 기준](#9-채점-기준)
10. [FAQ](#10-faq)

---

## 1. 시험 개요

### 목적

AI 코딩 에이전트(GitHub Copilot, Claude Code, Cursor 등)가 **순차적으로 변화하는 요구사항** 하에서 **구조적으로 건전한 코드**를 유지할 수 있는지 평가한다.

### 핵심 가설

> 대부분의 AI 코딩 에이전트는 단일 프롬프트 내에서는 깔끔한 코드를 생성하지만,
> 후속 단계에서 기존 코드의 **구조적 변경이 필요**한 경우 스파게티 코드를 유발한다.

### 평가 대상

- AI 코딩 에이전트의 **리팩토링 능력**
- **소급 적용(retroactive)** 요구사항 처리 능력
- **Cross-cutting concern** 통합 능력
- **Breaking change** 대응 시 하위 호환성 유지 능력

### 시험 형식

| 항목 | 내용 |
|------|------|
| 형식 | 순차적 프롬프트 기반 코드 생성 (8단계) |
| 언어 | Python |
| 평가 도구 | pytest (자동 채점) |
| 셋 수 | 4개 (C, D, E, F) |
| 셋당 소요 시간 | AI 에이전트 기준 약 10~30분 |

---

## 2. 시험 설계 철학

### 2.1 스파게티 유도 원리

각 테스트셋은 초반에 **깔끔한 기반 코드**를 작성하게 한 뒤, 후반부에서 **기존 코드의 구조적 변경을 강제**하는 요구사항을 제시한다. 이 과정에서 AI가:

1. 기존 코드를 적절히 리팩토링하는지
2. 새 코드를 기존 코드에 올바르게 통합하는지
3. 모든 관련 코드 경로에 변경을 전파하는지

를 검증한다.

### 2.2 공통 함정 패턴

모든 셋에 걸쳐 반복되는 6가지 핵심 패턴:

| # | 패턴 | 설명 | AI가 빠지는 이유 |
|---|------|------|-----------------|
| 1 | **소급 정책 적용** | 3단계 이후 "시스템 정책"을 기존 모든 코드에 적용 | AI가 새 코드에만 적용하고 기존 코드 수정을 누락 |
| 2 | **Cross-cutting Concern** | 모든 mutation에 공통 로직(이벤트/훅/인덱스) 삽입 | 일부 경로를 누락하거나 실행 순서를 잘못 설정 |
| 3 | **구조 교체** | 기존 자료구조/패턴을 완전히 다른 것으로 전환 | 기존 코드의 모든 사용처를 찾아 변경하지 못함 |
| 4 | **이중 실행 함정** | 내부 메서드 vs 공개 메서드 호출 시 로직 중복 | Command 패턴 등에서 공개 메서드를 호출하여 이중 실행 |
| 5 | **연쇄 효과** | 삭제/변경 시 관련 엔티티의 연쇄 처리 | 순환 참조, 연쇄 복원(undo) 등의 복잡한 상호작용 누락 |
| 6 | **하위 호환성** | 필드 추가/제거 시 기존 API와의 호환 | 새 형식만 지원하고 구 형식 처리를 빠뜨림 |

### 2.3 난이도 조절 원리

- **Step 1~2**: 기반 구축. 깔끔한 코드 생성 유도 (합격률 95%+)
- **Step 3~4**: 소급 적용 + Cross-cutting. 기존 코드 수정 강제 (합격률 70~85%)
- **Step 5~6**: 구조 교체 + 연쇄 효과. 깊은 리팩토링 필요 (합격률 50~70%)
- **Step 7~8**: 누적 복잡도 + 하위 호환. 전체 시스템 이해 필요 (합격률 40~60%)

---

## 3. 시험 셋 구성

### 3.1 셋 개요

| 셋 | 도메인 | 단계 | 소스 규모 | 테스트 수 | 핵심 함정 |
|----|--------|------|----------|----------|----------|
| **C** | 전자상거래 | 8 | 1,106 lines / 15 files | 133 | 이벤트 버스, 재고 예약 전환 |
| **D** | 태스크/프로젝트 관리 | 8 | 1,399 lines / 13 files | 222 | 훅 파이프라인, Undo/Redo, 연쇄 삭제 |
| **E** | 데이터 파이프라인 | 8 | 3,371 lines / 13 files | 206 | 스키마 진화, Lazy 전환, 레코드 불변성 |
| **F** | 메시징/알림 | 8 | 1,604 lines / 14 files | 220 | 스레딩, Soft Delete, 암호화 오버레이 |

### 3.2 셋 선택 기준

- **모든 셋**: 도메인 전문지식 없이 일반 개발자가 이해 가능
- **set-C**: 가장 범용적인 전자상거래 도메인. 원본 셋.
- **set-D**: 개발자에게 친숙한 Jira/Trello 패턴. 상태 관리 집중.
- **set-E**: 데이터 엔지니어링 관점. 불변성/스트리밍 패러다임 전환.
- **set-F**: 실시간 시스템 관점. 암호화/검색 cross-cutting 집중.

### 3.3 셋간 스파게티 패턴 매핑

| 패턴 | set-C | set-D | set-E | set-F |
|------|-------|-------|-------|-------|
| 소급 정책 | 시스템 정책(Step 3) | 권한 시스템(Step 3) | 스키마 진화(Step 4) | Access Control(Step 3) |
| Cross-cutting | EventBus(Step 4) | 훅 파이프라인(Step 4) | DLQ + 메트릭(Step 6~7) | 역색인 동기화(Step 6) |
| 구조 교체 | 직접차감→예약(Step 5) | 저장→계산 속성(Step 7) | Eager→Lazy(Step 5) | 평면→스레드(Step 4) |
| 이중 실행 | — | Undo/Redo(Step 5) | — | — |
| 연쇄 효과 | — | 연쇄 삭제(Step 6) | — | Soft Delete(Step 5) |
| 불변성/암호화 | — | — | 레코드 불변(Step 7) | 소급 암호화(Step 7) |
| 하위 호환 | Serializer(Step 6) | Serializer(Step 8) | Serializer(Step 1,8) | 암호화 공존(Step 7) |

---

## 4. 응시자 가이드 (AI 코딩 에이전트 운영자)

### 4.1 시험 환경 준비

```bash
# 저장소 클론
git clone <repository-url>
cd ai-sw-certificate

# Python 3.9+ 확인
python3 --version

# pytest 설치
pip install pytest
```

### 4.2 시험 진행 방법

**한 셋을 선택**하여 진행한다 (예: set-D).

#### Step 1: 시험 셋 디렉토리로 이동

```bash
cd set-D
```

#### Step 2: src/ 초기화

레퍼런스 구현이 포함되어 있으므로, 시험 전 src/ 내용을 초기화한다:

```bash
# src/ 내의 모든 .py 파일을 빈 파일로 초기화 (__init__.py 제외)
cd src
for f in *.py; do
  if [ "$f" != "__init__.py" ]; then
    echo "" > "$f"
  fi
done
cd ..
```

#### Step 3: 프롬프트 순차 제공

AI 코딩 에이전트에게 프롬프트를 **step1.md부터 step8.md까지 순서대로** 제공한다.

```
# 1단계
prompts/step1.md의 내용을 AI에게 전달 → 코드 생성 → src/에 저장

# 2단계
prompts/step2.md의 내용을 AI에게 전달 → 코드 생성/수정 → src/에 저장

# ... 8단계까지 반복
```

**중요 규칙**:
- 프롬프트는 **반드시 순서대로** 제공한다
- 각 단계에서 AI가 이전 단계의 코드를 **읽고 수정**할 수 있어야 한다
- AI에게 테스트 파일의 내용을 보여주지 않는다
- AI에게 추가 힌트나 수정 지시를 하지 않는다

#### Step 4: 단계별 검증 (선택)

각 단계 완료 후 해당 단계의 테스트를 실행하여 진행 상황을 확인할 수 있다:

```bash
# step 3까지 완료 후
python3 -m pytest tests/test_step1.py tests/test_step2.py tests/test_step3.py -v
```

#### Step 5: 최종 평가

모든 단계 완료 후 전체 테스트를 실행한다:

```bash
# 전체 테스트
python3 -m pytest tests/ -v

# 통합 테스트만 (핵심 평가)
python3 -m pytest tests/test_final.py -v
```

### 4.3 주의사항

- 프롬프트에 명시되지 않은 테스트 파일, README, 다른 셋의 코드를 AI에게 보여주지 않는다
- AI의 코드 생성 후 수동 수정을 하지 않는다
- 각 단계의 프롬프트를 한 번에 모두 주지 않고, **반드시 순차적으로** 제공한다
- 동일한 AI 세션/컨텍스트 내에서 모든 단계를 진행한다 (컨텍스트 유지)

---

## 5. 시험관 가이드 (평가자)

### 5.1 시험 실행 자동화

```bash
#!/bin/bash
# run_exam.sh — 특정 셋에 대한 시험 실행 및 결과 수집

SET_NAME=${1:-"set-D"}
RESULTS_DIR="results/${SET_NAME}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

cd "$SET_NAME"

# 전체 테스트 실행
python3 -m pytest tests/ -v --tb=short > "$RESULTS_DIR/full_results.txt" 2>&1

# 통합 테스트만
python3 -m pytest tests/test_final.py -v --tb=long > "$RESULTS_DIR/final_results.txt" 2>&1

# 단계별 테스트
for i in $(seq 1 8); do
  python3 -m pytest tests/test_step${i}.py -v --tb=short > "$RESULTS_DIR/step${i}_results.txt" 2>&1
done

# 요약
echo "=== 시험 결과 요약 ===" > "$RESULTS_DIR/summary.txt"
python3 -m pytest tests/ -v --tb=no 2>&1 | tail -1 >> "$RESULTS_DIR/summary.txt"
python3 -m pytest tests/test_final.py -v --tb=no 2>&1 | tail -1 >> "$RESULTS_DIR/summary.txt"

cat "$RESULTS_DIR/summary.txt"
```

### 5.2 결과 해석

#### 핵심 지표

| 지표 | 계산 방법 | 의미 |
|------|----------|------|
| **전체 통과율** | passed / total × 100 | 기본 기능 구현 능력 |
| **test_final 통과율** | test_final passed / test_final total × 100 | **구조적 품질 핵심 지표** |
| **후반부 통과율** | (step5~8 passed) / (step5~8 total) × 100 | 리팩토링/통합 능력 |
| **스파게티 점수** | 100 - test_final 통과율 | 높을수록 스파게티 코드 유발 |

#### 등급 기준 (test_final.py 기준)

| 등급 | test_final 통과율 | 해석 |
|------|------------------|------|
| **A** | 90% 이상 | 우수 — 구조적 리팩토링 능력 입증 |
| **B** | 75~89% | 양호 — 대부분의 통합 시나리오 처리 |
| **C** | 60~74% | 보통 — 일부 cross-cutting concern 누락 |
| **D** | 40~59% | 미흡 — 주요 구조 변경 실패 |
| **F** | 40% 미만 | 불합격 — 심각한 스파게티 코드 발생 |

### 5.3 실패 유형 분류

테스트 실패를 다음 카테고리로 분류하여 기록한다:

| 카테고리 | 코드 | 설명 | 예시 |
|----------|------|------|------|
| **소급 누락** | R | 소급 정책이 기존 코드에 미적용 | 대소문자 무시가 새 코드에만 적용됨 |
| **경로 누락** | P | 특정 실행 경로에서 로직 누락 | update로 상태 변경 시 완료 추적 안 됨 |
| **이중 실행** | D | 같은 로직이 두 번 실행 | Command가 public 메서드를 호출하여 훅 이중 실행 |
| **동기화 누락** | S | Cross-cutting 업데이트 누락 | 메시지 수정 시 검색 인덱스 미갱신 |
| **하위 호환** | B | 이전 형식과의 호환성 누락 | 새 직렬화 형식만 지원 |
| **방어적 복사** | C | 내부 상태 노출 | list/dict 참조를 그대로 반환 |
| **API 불일치** | A | 메서드 시그니처/반환값 불일치 | set_field()가 None을 반환 (새 Record를 반환해야 함) |

### 5.4 보고서 작성

```
# AI 코딩 에이전트 평가 보고서

## 기본 정보
- 평가 대상: [에이전트 이름 및 버전]
- 평가 셋: [set-C / set-D / set-E / set-F]
- 평가 일시: [YYYY-MM-DD]
- 평가자: [이름]

## 정량 결과
- 전체 통과율: [X/Y] (Z%)
- test_final 통과율: [X/Y] (Z%)
- 등급: [A/B/C/D/F]

## 단계별 통과율
| Step | Passed | Failed | Total | 통과율 |
|------|--------|--------|-------|--------|
| 1    |        |        |       |        |
| ...  |        |        |       |        |
| 8    |        |        |       |        |
| final|        |        |       |        |

## 실패 유형 분류
| 카테고리 | 건수 | 주요 사례 |
|----------|------|----------|
| 소급 누락(R) |   |          |
| 경로 누락(P) |   |          |
| ...          |   |          |

## 정성 평가
- 코드 구조 품질:
- 리팩토링 능력:
- 특이사항:
```

---

## 6. 셋별 상세 설계

### 6.1 set-C: 전자상거래 시스템

#### 도메인 설명
상품 카탈로그, 재고 관리, 장바구니, 주문, 할인, 리뷰, 쿠폰 시스템을 순차적으로 구축하는 전자상거래 플랫폼.

#### 파일 구조 (15 src files)
```
src/
  exceptions.py     # 커스텀 예외 (5종)
  models.py          # Product, Category, ProductStatus
  catalog.py         # ProductCatalog — 상품/카테고리 CRUD
  inventory.py       # InventoryManager — 재고 + 예약 시스템
  serializer.py      # 직렬화/역직렬화
  cart.py            # ShoppingCart — 장바구니
  pricing.py         # TaxCalculator, PricingEngine
  order.py           # Order, OrderLine, OrderStatus
  order_service.py   # OrderService — 주문 생성/취소/환불
  events.py          # Event, EventBus
  discounts.py       # Discount, DiscountEngine
  reviews.py         # Review, ReviewManager
  wishlist.py        # Wishlist
  coupons.py         # Coupon, CouponManager
  reports.py         # ReportGenerator
```

#### 단계별 함정 설계

| Step | 주제 | 함정 | 유도되는 문제 |
|------|------|------|-------------|
| 1 | 카탈로그 + 재고 | 없음 (기반) | — |
| 2 | 장바구니 + 가격 | 없음 (기반) | — |
| 3 | 주문 + 시스템 정책 | **weight 필드 소급 추가**, 대소문자 무시/방어적 복사 | AI가 기존 Product, Serializer를 수정하지 않음 |
| 4 | 이벤트 시스템 | **EventBus를 기존 4개 클래스에 주입** | 일부 클래스/메서드에서 이벤트 발행 누락 |
| 5 | 할인 + 예약 전환 | **직접 차감 → 예약/확인 패턴** | OrderService가 여전히 직접 차감하거나, 이중 차감 |
| 6 | 리뷰 + 위시리스트 | 리뷰 기반 정렬 추가 | 카탈로그에 review_manager 연동 누락 |
| 7 | 쿠폰 + 환불 | 환불 시 재고 복원 | 부분/전체 환불의 재고 처리 차이 |
| 8 | 검증 + 보고서 | 소급 검증 규칙 | 기존 add/update에 검증 미적용 |

---

### 6.2 set-D: 태스크/프로젝트 관리 시스템

#### 도메인 설명
Task, Project, User를 관리하는 Jira/Trello 스타일 시스템. 칸반 보드, 권한, 훅, Undo/Redo, 연쇄 삭제, 분석 기능을 순차적으로 추가.

#### 파일 구조 (13 src files)
```
src/
  exceptions.py      # 커스텀 예외 (10종)
  models.py           # Task, Project, User, TaskStatus, TaskPriority
  task_manager.py     # TaskManager — 태스크 CRUD + 필터링
  project_manager.py  # ProjectManager — 프로젝트 CRUD
  user_manager.py     # UserManager — 사용자 CRUD
  board.py            # Board — 칸반 보드, WIP 제한
  permissions.py      # PermissionChecker — 역할 기반 권한
  hooks.py            # HookPipeline, AuditLogHook, ValidationHook
  history.py          # HistoryManager, Command 패턴 (6종)
  relations.py        # RelationManager — 의존성, 코멘트
  analytics.py        # AnalyticsEngine — 속도, 워크로드, 번다운
  serializer.py       # TaskSerializer, ProjectSerializer, UserSerializer
```

#### 단계별 함정 설계

| Step | 주제 | 함정 | 유도되는 문제 |
|------|------|------|-------------|
| 1 | 기반 CRUD | 없음 | — |
| 2 | 칸반 보드 + 필터링 | 없음 | — |
| 3 | **권한 시스템 소급** | 기존 모든 CRUD에 optional user_id 추가 | AI가 어떤 메서드에 어떤 권한이 필요한지 잘못 판단 |
| 4 | **훅 파이프라인** | 모든 mutation을 before/after 훅으로 래핑 | 훅과 권한의 실행 순서 오류, 일부 메서드 래핑 누락 |
| 5 | **Undo/Redo** | Command가 _internal 메서드를 호출해야 함 | **핵심 트랩**: public 호출 시 훅/권한 이중 실행 |
| 6 | **연쇄 삭제** | 프로젝트 삭제 시 태스크/코멘트/의존성 연쇄 제거 | 연쇄 삭제 후 Undo로 전체 복원이 안 됨 |
| 7 | **계산 속성** | story_points가 metadata 기반 계산 속성으로 전환 | 기존 직접 할당 코드가 property에 의해 breaking change |
| 8 | 검증 + 직렬화 | 검증 소급 + 직렬화 하위 호환 | 구/신 형식 공존 처리 실패 |

#### 핵심 트랩 상세: Undo/Redo 이중 실행

```
[잘못된 구현]
CreateTaskCommand.execute()
  → task_manager.add_task()          # public 메서드
    → hook_pipeline.execute_before()  # 훅 실행 (1차)
    → permission_checker.check()      # 권한 체크 (1차)
    → _add_task_internal()            # 실제 로직

[올바른 구현]
CreateTaskCommand.execute()
  → task_manager._add_task_internal() # internal 메서드 직접 호출
    # 훅/권한 없이 순수 로직만 실행
```

---

### 6.3 set-E: 데이터 처리 파이프라인 시스템

#### 도메인 설명
Record, Schema, Processor, Pipeline을 기반으로 한 ETL 프레임워크. 스키마 진화, Lazy 실행, Dead Letter Queue, 레코드 불변성을 순차적으로 도입.

#### 파일 구조 (13 src files)
```
src/
  errors.py           # 커스텀 예외 (8종)
  record.py           # Record, Schema, RecordStatus
  validators.py       # Validator 계열 (Required, Type, Range, Composite)
  serializer.py       # RecordSerializer
  processors.py       # Filter, Transform, Enrich, Aggregate
  pipeline.py         # Pipeline — 프로세서 체인 실행
  router.py           # Router — 조건 기반 라우팅
  registry.py         # PipelineRegistry
  schema_registry.py  # SchemaRegistry + SchemaMigrator
  dead_letter.py      # DeadLetterQueue, DLQEntry
  metrics.py          # MetricsCollector
  reports.py          # ReportGenerator
```

#### 단계별 함정 설계

| Step | 주제 | 함정 | 유도되는 문제 |
|------|------|------|-------------|
| 1 | Record + Schema + Validator | 없음 | — |
| 2 | Processor + Pipeline | 없음 | — |
| 3 | Router + Registry + 정책 | **대소문자 무시/방어적 복사 소급** | 기존 코드에 정책 미적용 |
| 4 | **스키마 진화** | v1/v2 레코드 공존, 프로세서가 누락 필드 처리 | TransformProcessor가 v1 레코드의 누락 필드에서 크래시 |
| 5 | **Eager → Lazy 전환** | Pipeline.execute()가 generator 반환 | AggregateProcessor가 generator를 소비하지 못함 |
| 6 | **Fail-fast → DLQ** | DLQ 있으면 계속 처리, 없으면 기존 동작 | DLQ 분기 로직 누락으로 항상 중단 또는 항상 계속 |
| 7 | **레코드 불변성** | set_field()가 새 Record 반환 | AI가 반환값을 무시하고 원본 참조 유지 |
| 8 | 검증 + 보고서 | 체이닝 검증 + 실행 이력 | 프로세서 간 호환성 검증 로직 |

#### 핵심 트랩 상세: Record 불변성 전환

```python
# Step 1~6의 코드 (mutable)
record.set_field("name", "value")  # in-place 수정, 반환값 없음

# Step 7 이후 (immutable, copy-on-write)
new_record = record.set_field("name", "value")  # 새 Record 반환!
# record는 변경되지 않음

# AI가 빠지는 함정: 기존 프로세서 코드를 수정하지 않으면
# set_field의 반환값을 무시하여 변환이 사라짐
```

---

### 6.4 set-F: 메시징 & 알림 시스템

#### 도메인 설명
User, Channel, Message를 기반으로 한 Slack 스타일 메시징 시스템. 알림, 접근 제어, 스레딩, Soft Delete, 전문 검색, 암호화를 순차적으로 도입.

#### 파일 구조 (14 src files)
```
src/
  exceptions.py      # 커스텀 예외 (10종)
  models.py           # User, Channel, Message, UserStatus, ChannelType
  user_manager.py     # UserManager
  channel_manager.py  # ChannelManager
  message_manager.py  # MessageManager
  mention.py          # MentionParser
  notification.py     # NotificationManager, Notification
  access_control.py   # AccessController
  thread_manager.py   # ThreadManager
  search_index.py     # SearchIndex — 역색인
  encryption.py       # EncryptionManager — XOR+Base64
  audit.py            # AuditLogger, AuditEntry
  reports.py          # ReportGenerator
```

#### 단계별 함정 설계

| Step | 주제 | 함정 | 유도되는 문제 |
|------|------|------|-------------|
| 1 | User + Channel + Message | 없음 | — |
| 2 | 알림 + 멘션 | 없음 | — |
| 3 | **Access Control 소급** | 모든 메시지 CRUD에 채널 멤버십 확인 | 일부 메서드에서 권한 체크 누락 |
| 4 | **평면 → 스레드 전환** | get_messages()가 root만 반환 | 기존 메시지 수 계산, 검색 범위 의미 변경 |
| 5 | **Hard → Soft Delete** | 모든 조회에서 삭제 항목 필터링 | 일부 조회 메서드에서 필터링 누락 |
| 6 | **역색인 동기화** | 모든 mutation에 인덱스 업데이트 | 수정/삭제 시 인덱스 미갱신 |
| 7 | **소급 암호화** | 저장은 암호화, 반환은 복호화 | SearchIndex는 복호화된 내용으로 인덱싱해야 하는데 암호화된 내용을 인덱싱 |
| 8 | 검증 + 통계 + 보고서 | 메시지 검증 강화 | 금지어 필터가 기존 코드에 미적용 |

#### 핵심 트랩 상세: 암호화 + 검색 인덱스 충돌

```
[저장 흐름]
send_message(content="hello")
  → encrypt("hello") → "ENC:aGVsbG8="
  → store in _messages (encrypted)
  → search_index.index(???)  # 여기서 plaintext를 인덱싱해야 함!

[조회 흐름]
get_message(id)
  → load from _messages → "ENC:aGVsbG8="
  → decrypt → "hello"
  → return Message(content="hello")

[AI가 빠지는 함정]
- 인덱스에 암호화된 내용을 넣으면 검색 불가
- in-place 복호화하면 저장 상태가 오염됨
- 별도 plaintext 참조를 유지해야 함
```

---

## 7. 스파게티 유도 패턴 분석

### 7.1 패턴별 AI 실패 확률 (내부 검증 기반)

| 패턴 | 설명 | 실패 확률 | 난이도 |
|------|------|----------|--------|
| 방어적 복사 누락 | 프로퍼티 접근 시 참조 반환 | ~80% | 낮음 |
| 대소문자 무시 소급 | 기존 검색에 .lower() 미추가 | ~60% | 낮음 |
| Cross-cutting 경로 누락 | 일부 mutation에 공통 로직 미적용 | ~50% | 중간 |
| 구조 전환 파급 | Eager→Lazy, Mutable→Immutable 등 | ~70% | 높음 |
| 이중 실행 | 공개/내부 메서드 혼용 | ~60% | 높음 |
| 연쇄 복원 | 삭제 + undo의 전체 복원 | ~80% | 높음 |
| 암호화/인덱스 충돌 | 저장/조회/검색의 상태 불일치 | ~70% | 높음 |
| 하위 호환 직렬화 | 구/신 형식 모두 처리 | ~50% | 중간 |

### 7.2 함정이 효과적인 이유

1. **점진적 복잡도**: 초반에 깔끔한 코드를 작성하므로, 후반에 "이미 동작하는 코드를 건드리기 싫은" 경향
2. **명시적 vs 암묵적**: 프롬프트는 새 기능을 명시하지만, 기존 코드 수정은 암묵적으로 요구
3. **컨텍스트 한계**: 8단계까지 진행하면 전체 코드를 동시에 파악하기 어려움
4. **패턴 관성**: AI가 기존 패턴(예: mutable set_field)을 유지하려는 경향

---

## 8. 검증 결과 (내부용)

### 8.1 레퍼런스 구현 검증

모든 셋의 레퍼런스 구현은 전체 테스트를 통과한다:

| 셋 | 전체 통과 | test_final 통과 |
|----|----------|----------------|
| set-C | 130/133 (기존 3개 실패) | — |
| set-D | **222/222 (100%)** | 37/37 |
| set-E | **206/206 (100%)** | 34/34 |
| set-F | **220/220 (100%)** | 37/37 |

### 8.2 AI 에이전트 검증 (Claude Opus 4.6, 프롬프트만 제공)

| 셋 | 전체 | 통과율 | test_final | 통과율 | 스파게티 점수 |
|----|------|--------|-----------|--------|-------------|
| set-D | 189/222 | 85% | 27/37 | 73% | **27점** |
| set-E | 170/206 | 83% | 30/34 | 88% | **12점** |
| set-F | 181/220 | 82% | 30/37 | 81% | **19점** |

### 8.3 주요 실패 사례

#### set-D 실패 (10/37 final tests failed)
- 훅 키 네이밍 불일치 (`"stage"` vs `"phase"`)
- Cascade 삭제 후 Undo 복원 미구현
- 방어적 복사 누락 (tags, metadata 프로퍼티)
- 완료 추적 경로 불완전 (Board만 추적, update 경로 누락)
- 계산 속성이 to_dict()에 미포함

#### set-E 실패 (4/34 final tests failed)
- SchemaRegistry 대소문자 무시 미적용
- DLQ get_by_processor 대소문자 미적용
- 스키마 마이그레이션 + 파이프라인 통합 실패
- 직렬화 라운드트립에서 에러 목록 미보존

#### set-F 실패 (7/37 final tests failed)
- 모델 생성자 id 키워드 미지원
- 암호화 저장 상태 오염 (in-place 복호화)
- 감사 로그 액션 네이밍 불일치
- 채널명 중복 체크 대소문자 미처리
- `@all` 멘션 알림 미구현
- 삭제된 채널의 메시지 접근 처리 누락

---

## 9. 채점 기준

### 9.1 자동 채점 (pytest)

```bash
# 전체 점수 (100점 만점)
전체 점수 = (전체 통과 테스트 수 / 전체 테스트 수) × 100

# 구조 품질 점수 (100점 만점) — 핵심 지표
구조 점수 = (test_final 통과 수 / test_final 전체 수) × 100
```

### 9.2 권장 평가 체계

| 영역 | 배점 | 측정 방법 |
|------|------|----------|
| 기본 구현 (Step 1~2) | 20점 | test_step1 + test_step2 통과율 × 20 |
| 소급 적용 (Step 3~4) | 25점 | test_step3 + test_step4 통과율 × 25 |
| 구조 변경 (Step 5~6) | 25점 | test_step5 + test_step6 통과율 × 25 |
| 통합 완성 (Step 7~8) | 15점 | test_step7 + test_step8 통과율 × 15 |
| 구조적 일관성 | 15점 | test_final 통과율 × 15 |
| **총점** | **100점** | |

### 9.3 복수 셋 평가

여러 셋을 시험할 경우 최종 점수는 **각 셋 점수의 평균**으로 산출한다.

---

## 10. FAQ

### Q: 시험 중 AI에게 테스트 파일을 보여줘도 되나요?
**A: 아니요.** 테스트 파일을 보여주면 AI가 테스트를 통과하는 코드를 직접 작성하게 되어, 구조적 코드 품질이 아닌 테스트 맞춤 능력을 측정하게 됩니다.

### Q: AI가 이전 단계의 코드를 수정해도 되나요?
**A: 네.** 이것이 시험의 핵심입니다. 후속 단계에서 기존 코드를 적절히 리팩토링하는 것이 정답입니다.

### Q: 프롬프트를 한 번에 모두 주면 안 되나요?
**A: 안 됩니다.** 순차적 제공이 핵심입니다. 한 번에 주면 AI가 미리 전체 구조를 설계할 수 있어 스파게티 유도 효과가 사라집니다.

### Q: 어떤 셋을 먼저 시험해야 하나요?
**A:** 난이도 순서: set-C (기본) → set-F (중간) → set-E (중상) → set-D (상). 처음이라면 set-C 또는 set-F부터 시작을 권장합니다.

### Q: 동일한 AI에 같은 셋을 반복 시험하면 결과가 달라지나요?
**A: 네.** AI의 비결정적 특성상 결과가 달라질 수 있습니다. 신뢰도를 높이려면 3회 이상 반복하여 평균을 사용하세요.

### Q: 레퍼런스 구현을 수정해야 할 때는?
**A:** 레퍼런스 구현 수정 후 반드시 `pytest tests/ -v`로 전체 통과를 확인하세요. test_final.py가 핵심이므로, 통합 테스트의 의도를 변경하지 않도록 주의하세요.

### Q: 새로운 셋을 추가하려면?
**A:** 이 문서의 [섹션 2.2 공통 함정 패턴](#22-공통-함정-패턴)을 참고하여, 6가지 패턴 중 3~4개를 선택해 새 도메인에 적용하세요. set-C의 파일 구조를 템플릿으로 사용하면 됩니다.
