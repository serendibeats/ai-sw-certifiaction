# AI 코딩 에이전트 구조적 코드 품질 평가

AI 코딩 에이전트가 순차적 요구사항 변화에 대응하며 구조적으로 건전한 코드를 유지하는지 평가하는 시험 시스템.

## 구조

```
├── docs/
│   ├── EXAM_GUIDE.md       # 시험 가이드 (응시자 + 평가자)
│   └── REVIEW_REPORT.md    # 검증 리포트
├── set-C/                   # 전자상거래 (173 tests)
├── set-D/                   # 태스크/프로젝트 관리 (222 tests)
├── set-E/                   # 데이터 파이프라인 (206 tests)
├── set-F/                   # 메시징 & 알림 (220 tests)
└── run_exam.sh              # 시험 실행 스크립트
```

## 빠른 시작

### 레퍼런스 검증

```bash
./run_exam.sh set-D -v     # set-D 레퍼런스 구현 테스트
```

### 모의 시험 실행

```bash
./run_exam.sh set-D        # src/ 초기화 → 프롬프트 순차 제공 → 채점
```

### 수동 채점

```bash
cd set-D
python3 -m pytest tests/ -v                   # 전체 테스트
python3 -m pytest tests/test_final.py -v      # 통합 테스트 (핵심)
```

## 각 셋 개요

| 셋 | 도메인 | 소스 | 테스트 | 통합 테스트 |
|----|--------|:----:|:------:|:----------:|
| set-C | 전자상거래 | 1,056 lines / 16 files | 173 | 66 |
| set-D | 태스크 관리 | 1,472 lines / 13 files | 222 | 37 |
| set-E | 데이터 파이프라인 | 900 lines / 13 files | 206 | 34 |
| set-F | 메시징/알림 | 1,117 lines / 14 files | 220 | 39 |

## 상세 문서

- [시험 가이드](docs/EXAM_GUIDE.md) — 시험 설계, 진행 방법, 채점 기준
- [검증 리포트](docs/REVIEW_REPORT.md) — AI 검증 결과, 실패 분석

## 시험 원리

1. **Step 1~2**: 깔끔한 기반 코드 생성 (AI 대부분 통과)
2. **Step 3~4**: 소급 정책 + Cross-cutting 추가 (기존 코드 수정 필요)
3. **Step 5~6**: 구조 교체 + 연쇄 효과 (깊은 리팩토링 필요)
4. **Step 7~8**: 누적 복잡도 + 하위 호환 (전체 시스템 이해 필요)

후반부로 갈수록 AI가 **기존 코드의 구조적 변경을 올바르게 수행하지 못하면** 통합 테스트(test_final.py)에서 실패합니다.
