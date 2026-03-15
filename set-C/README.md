# 순차적 개발 시험 v2: 전자상거래 시스템

## 개요

5단계 순차 프롬프트로 AI Coding Agent에게 전자상거래 시스템을 구축하게 한 뒤,
최종 통합 테스트(test_final.py)로 코드 품질을 검증합니다.

## 스파게티 유도 설계

| Step | 코드 양 | 구조적 변화 |
|------|---------|------------|
| 1 | 400+ lines, 5 files | 대규모 기반 코드 생성 |
| 2 | 250+ lines, 2 files | Cart + Pricing 추가 |
| 3 | 300+ lines, 2 files | **Product에 weight 추가**, **시스템 정책 소급 적용** |
| 4 | 200+ lines, 2 files | **모든 파일에 이벤트 추가** (cross-cutting) |
| 5 | 300+ lines, 2 files | **할인+예약 시스템**, Cart/Inventory 구조 변경, OrderService 로직 삭제 |

## 핵심 함정

1. **암시적 소급 수정** (Step 3): "시스템 정책"으로 선언만 하고 어떤 파일을 수정할지는 AI가 판단
2. **Cross-cutting concern** (Step 4): 이벤트를 모든 mutation에 추가해야 하지만, 빠뜨리기 쉬움
3. **이중 경로 문제** (Step 5): Cart.add_item이 재고 예약을 하고, OrderService는 예약 확정
4. **기존 로직 삭제** (Step 5): OrderService의 직접 재고 차감을 예약 확정으로 교체

## 진행 방법

1. `prompts/step1.md` → AI가 `src/` 아래에 5개 파일 작성
2. `pytest tests/test_step1.py -v` → 통과 확인
3. ~ Step 5까지 반복
4. 최종: `pytest tests/test_final.py -v` → 크로스 스텝 검증

## 목표 코드량: 1500+ lines across 11+ files
