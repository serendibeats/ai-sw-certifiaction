# AI SW 역량 인증 테스트 — 파일럿 테스트셋

> AI 코딩 에이전트의 **구조적 코드 품질**을 평가하기 위한 AI SW 역량 인증 파일럿 테스트셋입니다.

**Repository**: https://github.com/serendibeats/ai-sw-certifiaction

## 개요

AI 코딩 에이전트에게 8단계 순차 프롬프트를 제공하여 시스템을 구축하게 한 뒤, 자동화된 테스트로 구조적 코드 품질을 평가합니다. 후반부 단계에서 기존 코드의 구조적 변경을 요구하여, AI가 스파게티 코드를 유발하는지 검증합니다.

## 구조

```
├── README.md                # 이 문서
├── run_exam.sh              # 시험 실행/검증 스크립트
├── docs/
│   ├── EXAM_GUIDE.md        # 시험 가이드 (설계 · 진행 · 채점)
│   └── REVIEW_REPORT.md     # 검증 리포트 (AI 결과 · 실패 분석)
├── set-C/                   # 전자상거래 시스템 (173 tests)
├── set-D/                   # 태스크/프로젝트 관리 (222 tests)
├── set-E/                   # 데이터 파이프라인 (206 tests)
└── set-F/                   # 메시징 & 알림 (220 tests)
```

## 빠른 시작

```bash
# 저장소 클론
git clone https://github.com/serendibeats/ai-sw-certifiaction.git
cd ai-sw-certifiaction

# Python 3.9+ 및 pytest 필요
pip install pytest

# 레퍼런스 구현 검증 (정답 코드가 모든 테스트를 통과하는지 확인)
./run_exam.sh set-D -v

# 모의 시험 실행 (src/ 초기화 후 AI에게 프롬프트 순차 제공)
./run_exam.sh set-D
```

## 테스트셋 구성

| 셋 | 도메인 | 소스 규모 | 전체 테스트 | 통합 테스트 |
|----|--------|:---------:|:----------:|:----------:|
| **set-C** | 전자상거래 | 1,056 lines / 16 files | 173 | 66 |
| **set-D** | 태스크/프로젝트 관리 | 1,472 lines / 13 files | 222 | 37 |
| **set-E** | 데이터 파이프라인 | 900 lines / 13 files | 206 | 34 |
| **set-F** | 메시징 & 알림 | 1,117 lines / 14 files | 220 | 39 |

각 셋은 독립적이며, 도메인 전문지식 없이 일반 개발자가 접근 가능합니다.

## 시험 원리

1. **Step 1~2**: 깔끔한 기반 코드 생성 (AI 대부분 통과)
2. **Step 3~4**: 소급 정책 + Cross-cutting 추가 (기존 코드 수정 필요)
3. **Step 5~6**: 구조 교체 + 연쇄 효과 (깊은 리팩토링 필요)
4. **Step 7~8**: 누적 복잡도 + 하위 호환 (전체 시스템 이해 필요)

후반부로 갈수록 AI가 기존 코드의 구조적 변경을 올바르게 수행하지 못하면 **통합 테스트(test_final.py)에서 실패**합니다.

## 채점

```bash
cd set-D
python3 -m pytest tests/ -v                   # 전체 테스트
python3 -m pytest tests/test_final.py -v      # 통합 테스트 (핵심 지표)
```

| 등급 | test_final 통과율 | 해석 |
|:----:|:-----------------:|------|
| A | 90%+ | 우수 — 구조적 리팩토링 능력 입증 |
| B | 75~89% | 양호 — 대부분의 통합 시나리오 처리 |
| C | 60~74% | 보통 — 일부 cross-cutting concern 누락 |
| D | 40~59% | 미흡 — 주요 구조 변경 실패 |
| F | 40% 미만 | 불합격 — 심각한 스파게티 코드 발생 |

## 상세 문서

- **[시험 가이드](docs/EXAM_GUIDE.md)** — 시험 설계 철학, 진행 방법, 채점 기준, 셋별 상세 설계
- **[검증 리포트](docs/REVIEW_REPORT.md)** — Claude Opus 4.6 검증 결과, 실패 유형 분석
