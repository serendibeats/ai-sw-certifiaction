# AI SW 역량 인증 시험 — 채점자 가이드

## 구성

```
├── grader-C~F/              # 채점용 테스트 (src/는 빈 상태)
├── reference-C~F/           # 참조 구현 (100% 통과 레퍼런스)
├── run_grading.sh           # 채점 자동화 스크립트
├── run_reference_check.sh   # 참조 구현 검증 스크립트
└── docs/
    ├── EXAM_GUIDE.md        # 시험 설계 · 진행 · 채점 상세
    └── REVIEW_REPORT.md     # AI 검증 결과 · 실패 유형 분석
```

| 셋 | 도메인 | 전체 테스트 | test_final |
|----|--------|:----------:|:----------:|
| C | 전자상거래 | 173 | 66 |
| D | 태스크/프로젝트 관리 | 222 | 37 |
| E | 데이터 파이프라인 | 206 | 34 |
| F | 메시징 & 알림 | 220 | 39 |

## 채점 방법

### 1. 참조 구현 검증 (선택)

```bash
./run_reference_check.sh              # 전체 검증
./run_reference_check.sh reference-C  # 특정 셋만
```

### 2. 응시자 제출물 채점

```bash
./run_grading.sh grader-C candidate-C/src/
./run_grading.sh grader-D candidate-D/src/
```

### 3. 등급 기준

test_final.py 통과율 기반:

| 등급 | test_final 통과율 | 해석 |
|:----:|:-----------------:|------|
| A | 90%+ | 우수 — 구조적 리팩토링 능력 입증 |
| B | 75~89% | 양호 — 대부분의 통합 시나리오 처리 |
| C | 60~74% | 보통 — 일부 cross-cutting concern 누락 |
| D | 40~59% | 미흡 — 주요 구조 변경 실패 |
| F | 40% 미만 | 불합격 — 심각한 스파게티 코드 발생 |

## 상세 문서

- **[시험 가이드](docs/EXAM_GUIDE.md)** — 시험 설계 철학, 진행 방법, 채점 기준
- **[검증 리포트](docs/REVIEW_REPORT.md)** — Claude Opus 4.6 검증 결과, 실패 유형 분석

## 배포판 재빌드

테스트를 수정하여 재빌드가 필요한 경우, `_build/` 디렉토리의 도구를 사용합니다.

```bash
# 빌드 요구사항 (빌드 머신에만 필요)
sudo apt install python3-dev gcc
pip install cython

# 배포판 재생성
cd _build && bash build_candidate_dist.sh
```

빌드 환경: Ubuntu 24.04 LTS, Python 3.12, x86_64
