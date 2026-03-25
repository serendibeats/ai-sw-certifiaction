# AI SW 역량 인증 시험

8단계 순차 프롬프트 기반 코드 생성 시험입니다. AI 코딩 에이전트를 활용하여 시스템을 구축합니다.

## 환경 요구사항

- **Ubuntu 24.04 LTS, x86_64** (필수 — 테스트 바이너리가 이 환경 전용입니다)
- **Python 3.12** (정확히 3.12 필요)
- pytest (`pip install pytest`)

## 테스트셋

| 셋 | 도메인 |
|----|--------|
| **candidate-C** | 전자상거래 시스템 |
| **candidate-D** | 태스크/프로젝트 관리 |
| **candidate-E** | 데이터 파이프라인 |
| **candidate-F** | 메시징 & 알림 |

각 셋은 독립적이며, 하나를 선택하여 시험을 진행합니다.

## 진행 방법

```bash
# 1. 셋 디렉토리로 이동
cd candidate-C

# 2. Step 1 프롬프트 확인 (prompts/step1.md에 있음)
python3 exam_runner.py show

# 3. AI 에이전트에게 프롬프트를 제공하여 src/ 에 코드 생성

# 4. 테스트 통과 확인 + 다음 단계 프롬프트 해제
python3 exam_runner.py next

# 5. Step 2 ~ Step 8까지 반복
```

## 시험 러너 명령어

```bash
python3 exam_runner.py status    # 현재 진행 상태 확인
python3 exam_runner.py show      # 현재 단계 프롬프트 표시
python3 exam_runner.py test      # 현재 단계 테스트 실행
python3 exam_runner.py next      # 테스트 통과 후 다음 단계로
python3 exam_runner.py prev      # 이전 단계로 돌아가기
```

- `next` 시 현재 프롬프트가 삭제되고, 다음 프롬프트만 `prompts/`에 저장됩니다.
- `prev` 시 현재 프롬프트가 삭제되고, 이전 프롬프트가 복원됩니다.
- `prompts/`에는 항상 현재 단계의 프롬프트 파일 하나만 존재합니다.

## 시험 규칙

- **순서 엄수**: step1 → step2 → ... → step8 순서대로 진행
- **테스트 미공개**: `prompts/stepN.md` 요구사항만 보고 구현합니다. 테스트 파일의 내용을 참조하지 않습니다.
- **테스트 바이너리**: 테스트는 네이티브 바이너리(`.so`)로 제공되며, 소스 코드는 제공되지 않습니다.
- **한 세션 권장**: 같은 대화/세션에서 step1~8을 이어서 진행하여 컨텍스트를 유지합니다.
- **이전 단계 수정 허용**: 후속 단계에서 이전 코드를 수정하는 것은 허용됩니다.
