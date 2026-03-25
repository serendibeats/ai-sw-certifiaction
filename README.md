# AI SW 역량 인증 시험

> AI 코딩 에이전트의 **구조적 코드 품질**을 평가하기 위한 8단계 순차 프롬프트 기반 시험입니다.

## 구조

```
├── candidate-C/          # 응시자용 — 전자상거래 시스템
├── candidate-D/          # 응시자용 — 태스크/프로젝트 관리
├── candidate-E/          # 응시자용 — 데이터 파이프라인
├── candidate-F/          # 응시자용 — 메시징 & 알림
│
├── grader-C~F/           # 채점자용 — 테스트 소스 + test_final (src/ 는 빈 상태)
├── reference-C~F/        # 참조 구현 — 100% 통과 레퍼런스 코드
│
├── candidate-README.md   # 응시자 안내
├── grader-README.md      # 채점자 안내
├── run_grading.sh        # 채점 자동화 스크립트
├── run_reference_check.sh # 참조 구현 검증 스크립트
├── docs/                 # 시험 설계 · 검증 리포트
└── _build/               # 빌드 원본 및 도구 (재빌드 시에만 사용)
```

- **candidate-X**: src/ 비어있음, 테스트는 `.so` 네이티브 바이너리, test_final 미포함
- **grader-X**: src/ 빈 상태 (채점 시 candidate 코드 복사), 전체 테스트 소스 + test_final 포함
- **reference-X**: 전체 테스트 100% 통과하는 참조 구현 (읽기 전용)

## 사용 방법

### 응시자

```bash
cd candidate-C
python3 exam_runner.py show      # Step 1 프롬프트 확인
# AI 에이전트에게 프롬프트를 제공하여 src/ 에 코드 구현
python3 exam_runner.py next      # 테스트 통과 후 다음 단계로
# step1 ~ step8 반복
```

### 채점자

```bash
# 자동 채점 (권장)
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

## 상세 문서

- **[시험 가이드](docs/EXAM_GUIDE.md)** — 시험 설계 철학, 진행 방법, 채점 기준
- **[검증 리포트](docs/REVIEW_REPORT.md)** — AI 검증 결과, 실패 유형 분석
