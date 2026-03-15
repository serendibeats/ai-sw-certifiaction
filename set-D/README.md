# 순차적 개발 시험: 태스크/프로젝트 관리 시스템

## 개요

8단계 순차 프롬프트로 AI Coding Agent에게 태스크/프로젝트 관리 시스템을 구축하게 한 뒤,
최종 통합 테스트(test_final.py)로 코드 품질을 검증합니다.

## 스파게티 유도 설계

| Step | 코드 양 | 구조적 변화 |
|------|---------|------------|
| 1 | 450+ lines, 5 files | 대규모 기반 코드 생성 (Task, Project, User) |
| 2 | 250+ lines, 2 files | Board + 고급 필터링 추가 |
| 3 | 300+ lines, 5 files | **권한 시스템 소급 적용** — 모든 매니저에 permission 추가 |
| 4 | 300+ lines, 5 files | **훅 파이프라인** — 모든 mutation에 cross-cutting 훅 추가 |
| 5 | 350+ lines, 5 files | **Undo/Redo 스택** — Command 패턴, 내부 메서드 분리 필수 |
| 6 | 300+ lines, 4 files | **캐스케이드 삭제 + 엔터티 관계** — 순환 참조 감지 |
| 7 | 300+ lines, 5 files | **계산 프로퍼티 마이그레이션** — story_points/progress 변경 |
| 8 | 250+ lines, 4 files | **직렬화 + 유효성 검증 + 보고서** |

## 핵심 함정

1. **권한 시스템 소급 수정** (Step 3): "시스템 정책"으로 선언만 하고 어떤 파일을 수정할지는 AI가 판단
2. **Cross-cutting concern** (Step 4): 훅을 모든 mutation에 추가해야 하지만, 빠뜨리기 쉬움
3. **이중 실행 문제** (Step 5): Command가 public 메서드를 호출하면 훅/권한이 2회 실행
4. **순환 참조 감지** (Step 6): 의존성 그래프에서 사이클 감지 필요
5. **계산 프로퍼티 변경** (Step 7): story_points가 직접 필드에서 계산 프로퍼티로 변경
6. **직렬화 하위 호환** (Step 8): 이전 포맷과 새 포맷 모두 역직렬화 가능해야 함

## 파일 구조

```
set-D/
  conftest.py
  README.md
  prompts/step1.md ~ step8.md
  src/
    __init__.py
    exceptions.py
    models.py
    project_manager.py
    task_manager.py
    user_manager.py
    board.py
    permissions.py
    hooks.py
    history.py
    relations.py
    analytics.py
    serializer.py
  tests/
    __init__.py
    test_step1.py ~ test_step8.py
    test_final.py
```

## 진행 방법

1. `prompts/step1.md` → AI가 `src/` 아래에 파일 작성
2. `pytest tests/test_step1.py -v` → 통과 확인
3. ~ Step 8까지 반복
4. 최종: `pytest tests/test_final.py -v` → 크로스 스텝 검증

## 목표 코드량: 2200+ lines across 13+ files
