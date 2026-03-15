# 순차적 개발 시험: 데이터 처리 파이프라인 시스템

## 개요

8단계 순차 프롬프트로 AI Coding Agent에게 데이터 처리 파이프라인 시스템을 구축하게 한 뒤,
최종 통합 테스트(test_final.py)로 코드 품질을 검증합니다.

## 스파게티 유도 설계

| Step | 코드 양 | 구조적 변화 |
|------|---------|------------|
| 1 | 400+ lines, 4 files | 대규모 기반 코드 생성 (Record, Schema, Validators, Serializer) |
| 2 | 350+ lines, 2 files | Processor + Pipeline 추가 |
| 3 | 300+ lines, 2 files | Router + Registry, **시스템 정책 소급 적용** (대소문자 무시, 방어적 복사) |
| 4 | 300+ lines, 4 files | SchemaRegistry + SchemaMigrator, **스키마 마이그레이션 함정** |
| 5 | 350+ lines, 4 files | **Eager→Lazy 전환**, 우선순위 라우팅 |
| 6 | 300+ lines, 4 files | **Fail-Fast→DLQ 전환**, 에러 복구 |
| 7 | 350+ lines, 5 files | MetricsCollector, **Record 불변성 (set_field 반환값 변경)** |
| 8 | 250+ lines, 4 files | 검증 강화, 리포트, 체인 검증 |

## 핵심 함정

1. **시스템 정책 소급 수정** (Step 3): 대소문자 무시 + 방어적 복사를 기존 모든 코드에 적용
2. **스키마 마이그레이션** (Step 4): 프로세서가 누락 필드를 처리하도록 수정 필요
3. **Eager→Lazy 전환** (Step 5): Pipeline.execute()가 generator를 반환하도록 변경
4. **Fail-Fast→DLQ 전환** (Step 6): DLQ 유무에 따른 이중 동작 경로
5. **Record 불변성** (Step 7): set_field()가 새 Record를 반환, 모든 프로세서 수정 필요
6. **검증 체인** (Step 8): 파이프라인 체인 검증 + 실행 이력

## 진행 방법

1. `prompts/step1.md` → AI가 `src/` 아래에 파일 작성
2. `pytest tests/test_step1.py -v` → 통과 확인
3. ~ Step 8까지 반복
4. 최종: `pytest tests/test_final.py -v` → 크로스 스텝 검증

## 목표 코드량: 2200+ lines across 13+ files
