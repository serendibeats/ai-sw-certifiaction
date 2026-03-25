# 순차적 개발 시험: 태스크/프로젝트 관리 시스템

## 개요

8단계 순차 프롬프트로 AI 코딩 에이전트에게 태스크/프로젝트 관리 시스템을 구축하게 한 뒤,
통합 테스트(test_final.py)로 구조적 코드 품질을 검증합니다.

## 테스트 현황

- 레퍼런스 구현: 13 files, 1,472 lines
- 전체 테스트: 222개 (test_final: 37개)
- 레퍼런스 통과율: 222/222 (100%)

## 단계별 설계

| Step | 주제 | 핵심 함정 |
|------|------|----------|
| 1 | Task/Project/User 기반 CRUD | — |
| 2 | 칸반 보드 + 고급 필터링 | — |
| 3 | 권한 시스템 소급 적용 | 모든 매니저에 permission 추가, 시스템 정책 |
| 4 | 훅 파이프라인 | 모든 mutation에 before/after 훅 |
| 5 | Undo/Redo 스택 | **핵심**: public 호출 시 훅/권한 이중 실행 |
| 6 | 연쇄 삭제 + 엔티티 관계 | 순환 참조 감지, Undo로 전체 복원 |
| 7 | 계산 속성 마이그레이션 | story_points/progress가 계산 속성으로 전환 |
| 8 | 검증 + 직렬화 + 보고서 | 구/신 형식 하위 호환 |

## 진행 방법

```bash
# 1. src/ 초기화
cd src && for f in *.py; do [ "$f" != "__init__.py" ] && rm "$f"; done && cd ..

# 2. 프롬프트 순차 제공 (step1.md → step8.md)

# 3. 채점
python3 -m pytest tests/ -v                   # 전체
python3 -m pytest tests/test_final.py -v      # 핵심
```

상세 가이드: [docs/EXAM_GUIDE.md](../docs/EXAM_GUIDE.md)
