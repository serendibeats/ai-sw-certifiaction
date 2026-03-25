# 데이터 처리 파이프라인 시스템

8단계 순차 프롬프트 기반 코드 생성 시험입니다.

## 환경 요구사항

- **Ubuntu 24.04 LTS, x86_64** (필수 — 테스트 바이너리가 이 환경 전용)
- **Python 3.12**
- pytest (`pip install pytest`)

## 진행 방법

```bash
python3 exam_runner.py show      # 현재 단계 프롬프트 확인
# AI 에이전트에게 프롬프트를 제공하여 src/에 코드 생성
python3 exam_runner.py test      # 현재 단계 테스트 실행
python3 exam_runner.py next      # 테스트 통과 후 다음 단계로
python3 exam_runner.py prev      # 이전 단계로 돌아가기
python3 exam_runner.py status    # 현재 진행 상태 확인
```

`prompts/`에는 현재 단계의 프롬프트 파일만 존재합니다. `next`/`prev` 시 자동으로 교체됩니다.

## 규칙

- **순서 엄수**: step1 → step2 → ... → step8 순서대로 진행
- **프롬프트만 참고**: `prompts/stepN.md` 요구사항만 보고 구현. 테스트 파일은 참조하지 않음
- **테스트 바이너리**: 테스트는 `.so`로 제공되며 소스 코드 비공개
- **이전 단계 수정 허용**: 후속 단계에서 이전 코드 수정 가능
- **한 세션 권장**: 같은 대화/세션에서 step1~8을 이어서 진행
