# 메시징 & 알림 시스템

## 진행 방법

```bash
python3 exam_runner.py show      # 현재 단계 프롬프트 확인
# AI 에이전트에게 프롬프트를 제공하여 src/에 코드 생성
python3 exam_runner.py next      # 테스트 통과 후 다음 단계로
```

Step 1 프롬프트는 `prompts/step1.md`에 있습니다. Step 2~8은 이전 단계 통과 후 자동 해제됩니다.

## 규칙

- **순서 엄수**: step1 → step2 → ... → step8 순서대로 진행
- **프롬프트만 참고**: `prompts/stepN.md` 요구사항만 보고 구현
- **이전 단계 수정 허용**: 후속 단계에서 이전 코드 수정 가능
- **한 세션 권장**: 같은 대화/세션에서 step1~8을 이어서 진행
