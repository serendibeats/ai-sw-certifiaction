# 순차적 개발 시험: 데이터 처리 파이프라인 시스템

## 개요

8단계 순차 프롬프트로 AI 코딩 에이전트에게 데이터 처리 파이프라인 시스템을 구축하게 한 뒤,
통합 테스트(test_final.py)로 구조적 코드 품질을 검증합니다.

## 테스트 현황

- 레퍼런스 구현: 13 files, 900 lines
- 전체 테스트: 206개 (test_final: 34개)
- 레퍼런스 통과율: 206/206 (100%)

## 단계별 설계

| Step | 주제 | 핵심 함정 |
|------|------|----------|
| 1 | Record + Schema + Validator | — |
| 2 | Processor + Pipeline | — |
| 3 | Router + Registry + 시스템 정책 | 대소문자 무시/방어적 복사 소급 |
| 4 | 스키마 진화 | v1/v2 레코드 공존, 누락 필드 처리 |
| 5 | Eager → Lazy 전환 | Pipeline.execute()가 generator 반환 |
| 6 | Fail-fast → Dead Letter Queue | DLQ 유무에 따른 분기 처리 |
| 7 | 레코드 불변성 | set_field()가 새 Record 반환 (copy-on-write) |
| 8 | 검증 + 보고서 + 체이닝 검증 | 실행 이력, 프로세서 호환성 검증 |

## 진행 방법

```bash
# 1. src/ 초기화
cd src && for f in *.py; do [ "$f" != "__init__.py" ] && echo "" > "$f"; done && cd ..

# 2. 프롬프트 순차 제공 (step1.md → step8.md)

# 3. 채점
python3 -m pytest tests/ -v                   # 전체
python3 -m pytest tests/test_final.py -v      # 핵심
```

상세 가이드: [docs/EXAM_GUIDE.md](../docs/EXAM_GUIDE.md)
