# 순차적 개발 시험: 메시징 & 알림 시스템

## 개요

8단계 순차 프롬프트로 AI Coding Agent에게 메시징 & 알림 시스템을 구축하게 한 뒤,
최종 통합 테스트(test_final.py)로 코드 품질을 검증합니다.

## 스파게티 유도 설계

| Step | 코드 양 | 구조적 변화 |
|------|---------|------------|
| 1 | 400+ lines, 5 files | 대규모 기반 코드 생성 (User, Channel, Message) |
| 2 | 250+ lines, 2 files | Notification + Mention 파싱 추가, MessageManager 통합 |
| 3 | 300+ lines, 1 file | **접근 제어 소급 적용** — 모든 기존 코드에 권한 체크 추가 |
| 4 | 250+ lines, 1 file | **메시지 스레딩** — 평면 구조를 트리로 변환, get_messages 의미 변경 |
| 5 | 300+ lines, 변경 | **하드 삭제→소프트 삭제 전환**, 모든 쿼리 메서드 필터링, 레이트 리미팅 |
| 6 | 250+ lines, 1 file | **검색 인덱스** — 모든 mutation에 동기화 필요 (cross-cutting) |
| 7 | 300+ lines, 2 files | **암호화 오버레이** + 감사 로그, 기존 전체 코드에 영향 |
| 8 | 250+ lines, 1 file | 메시지 검증, 채널 통계, 리포트 생성 |

## 핵심 함정

1. **접근 제어 소급 적용** (Step 3): 기존 MessageManager, NotificationManager에 권한 체크를 추가해야 하지만 어떤 메서드를 수정할지 AI가 판단해야 함
2. **평면→트리 구조 변환** (Step 4): get_messages()는 루트 메시지만, search_messages()는 전체를 반환해야 함
3. **하드→소프트 삭제 전환** (Step 5): 모든 쿼리 메서드에서 삭제된 항목을 필터링해야 함
4. **Cross-cutting 검색 동기화** (Step 6): 모든 mutation(전송/편집/삭제/스레드)에서 인덱스 동기화 필요
5. **암호화 오버레이** (Step 7): 저장은 암호문, 반환은 평문, 검색 인덱스는 평문으로 구축해야 함

## 진행 방법

1. `prompts/step1.md` → AI가 `src/` 아래에 파일 작성
2. `pytest tests/test_step1.py -v` → 통과 확인
3. ~ Step 8까지 반복
4. 최종: `pytest tests/test_final.py -v` → 크로스 스텝 검증

## 목표 코드량: 2000+ lines across 14 files
