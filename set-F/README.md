# 순차적 개발 시험: 메시징 & 알림 시스템

## 개요

8단계 순차 프롬프트로 AI 코딩 에이전트에게 메시징 & 알림 시스템을 구축하게 한 뒤,
통합 테스트(test_final.py)로 구조적 코드 품질을 검증합니다.

## 테스트 현황

- 레퍼런스 구현: 14 files, 1,117 lines
- 전체 테스트: 220개 (test_final: 39개)
- 레퍼런스 통과율: 220/220 (100%)

## 단계별 설계

| Step | 주제 | 핵심 함정 |
|------|------|----------|
| 1 | User + Channel + Message 기반 | — |
| 2 | 알림 + 멘션 파싱 | — |
| 3 | Access Control 소급 적용 | 모든 메시지 CRUD에 채널 멤버십 확인 |
| 4 | 메시지 스레딩 | 평면→트리, get_messages가 root만 반환 |
| 5 | Soft Delete + Rate Limiting | 모든 조회에서 삭제 항목 필터링 |
| 6 | 전문 검색 인덱스 | 모든 mutation에 인덱스 동기화 |
| 7 | 소급 암호화 + 감사 로그 | 저장=암호문, 반환=평문, 인덱스=평문 |
| 8 | 메시지 검증 + 채널 통계 + 보고서 | 검증 규칙 강화 |

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
