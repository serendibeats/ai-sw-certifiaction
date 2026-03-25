# AI SW 역량 인증 시험

> AI 코딩 에이전트의 **구조적 코드 품질**을 평가하기 위한 8단계 순차 프롬프트 기반 시험입니다.

## 구조

```
├── candidate-C/          # 응시자용 — 전자상거래 시스템
├── candidate-D/          # 응시자용 — 태스크/프로젝트 관리
├── candidate-E/          # 응시자용 — 데이터 파이프라인
├── candidate-F/          # 응시자용 — 메시징 & 알림
│
├── grader-C~F/           # 채점용 테스트 (src/에 __init__.py만 존재)
├── reference-C~F/        # 참조 구현 — 100% 통과 레퍼런스 코드
│
├── run_grading.sh        # 채점 자동화 스크립트
├── run_reference_check.sh # 참조 구현 검증 스크립트
├── docs/                 # 시험 설계 · 검증 리포트
└── _build/               # 빌드 원본 및 도구 (재빌드 시에만 사용)
```

## 응시 방법

각 candidate-X/ 폴더의 README를 참고하세요. 요약:

```bash
cd candidate-C
python3 exam_runner.py show      # 현재 단계 프롬프트 확인
python3 exam_runner.py test      # 현재 단계 테스트 실행
python3 exam_runner.py next      # 테스트 통과 후 다음 단계로
python3 exam_runner.py prev      # 이전 단계로 돌아가기
```

이미 통과한 단계는 `next` 시 테스트 없이 바로 넘어갑니다.

## 채점 방법

```bash
# 자동 채점
./run_grading.sh grader-C candidate-C/src/

# 참조 구현 검증
./run_reference_check.sh
```

### 등급 기준

test_final.py 통과율 기반:

| 등급 | test_final 통과율 | 해석 |
|:----:|:-----------------:|------|
| A | 90%+ | 우수 — 구조적 리팩토링 능력 입증 |
| B | 75~89% | 양호 — 대부분의 통합 시나리오 처리 |
| C | 60~74% | 보통 — 일부 cross-cutting concern 누락 |
| D | 40~59% | 미흡 — 주요 구조 변경 실패 |
| F | 40% 미만 | 불합격 — 심각한 스파게티 코드 발생 |

## 환경 요구사항

- **응시자**: Ubuntu 24.04 LTS, Python 3.12, x86_64, pytest
- **채점자**: Python 3.12, pytest

## 배포판 재빌드

```bash
cd _build && bash build_candidate_dist.sh
```

빌드 요구사항: Ubuntu 24.04 LTS, Python 3.12, Cython, gcc, python3-dev

## 상세 문서

- **[시험 가이드](docs/EXAM_GUIDE.md)** — 시험 설계 철학, 진행 방법, 채점 기준
- **[검증 리포트](docs/REVIEW_REPORT.md)** — AI 검증 결과, 실패 유형 분석
