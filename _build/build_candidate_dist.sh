#!/bin/bash
# AI SW 역량 인증 시험 — 배포판 빌드 스크립트
#
# 사용법:
#   cd _build && ./build_candidate_dist.sh
#
# _build/ 내 원본 소스에서 프로젝트 루트에 배포판을 생성합니다:
#   ../candidate-C ~ F  — 응시자용 (테스트 .so 바이너리, src/ 비움, test_final 제거)
#   ../grader-C ~ F     — 채점자용 (전체 테스트 소스 + 참조 구현)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON=${PYTHON:-python3}
SETS="C D E F"

PY_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

# Cython + gcc 의존성 확인
if ! $PYTHON -c "import Cython" 2>/dev/null; then
    echo "ERROR: Cython이 설치되지 않았습니다. pip install cython" >&2
    exit 1
fi
if ! command -v gcc &>/dev/null; then
    echo "ERROR: gcc가 설치되지 않았습니다. sudo apt install gcc" >&2
    exit 1
fi
if [ ! -f "/usr/include/python${PY_VERSION}/Python.h" ]; then
    echo "ERROR: Python 개발 헤더가 없습니다. sudo apt install python3-dev" >&2
    exit 1
fi

echo "=== AI SW 역량 인증 시험 — 배포판 빌드 ==="
echo ""
echo "Python: $PY_VERSION"
echo "원본:   $SCRIPT_DIR/"
echo "출력:   $ROOT_DIR/"
echo ""

# ===========================
# 1. 채점자용 빌드 (원본 복사)
# ===========================
echo "--- 채점자용 빌드 ---"

for L in $SETS; do
    SET="set-${L}"
    TARGET="$ROOT_DIR/grader-${L}"
    echo "  grader-${L} 생성..."

    rm -rf "$TARGET"
    cp -r "$SCRIPT_DIR/$SET" "$TARGET"

    # __pycache__ 정리
    find "$TARGET" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find "$TARGET" -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
done

# docs 복사
if [ -d "$SCRIPT_DIR/docs" ]; then
    rm -rf "$ROOT_DIR/docs"
    cp -r "$SCRIPT_DIR/docs" "$ROOT_DIR/docs"
fi

# 채점자용 README
cp "$SCRIPT_DIR/grader_README.md" "$ROOT_DIR/grader-README.md"

echo "  채점자용 완료."
echo ""

# ===========================
# 2. 응시자용 빌드 (보호 적용)
# ===========================
echo "--- 응시자용 빌드 ---"

for L in $SETS; do
    SET="set-${L}"
    TARGET="$ROOT_DIR/candidate-${L}"
    echo "  candidate-${L} 처리 중..."

    rm -rf "$TARGET"
    cp -r "$SCRIPT_DIR/$SET" "$TARGET"

    # --- src/ 비우기 ---
    for f in "$TARGET/src/"*.py; do
        fname=$(basename "$f")
        if [ "$fname" != "__init__.py" ]; then
            echo "# TODO: implement this module" > "$f"
        fi
    done

    # --- __pycache__ 정리 (빌드 전 깨끗한 상태) ---
    find "$TARGET" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find "$TARGET" -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

    # --- 테스트 컴파일: Cython .so 네이티브 바이너리로 컴파일 ---
    rm -f "$TARGET/tests/test_final.py"
    $PYTHON "$SCRIPT_DIR/build_cython_tests.py" "$SCRIPT_DIR/$SET/tests" "$TARGET/tests"

    # --- src/__pycache__ 제거 ---
    rm -rf "$TARGET/src/__pycache__"

    # --- 셋별 README 정리 ---
    DOMAIN=$(head -1 "$TARGET/README.md" | sed 's/^#* *순차적 개발 시험: *//')
    cat > "$TARGET/README.md" << SETREADME
# $DOMAIN

## 진행 방법

\`\`\`bash
python3 exam_runner.py show      # 현재 단계 프롬프트 확인
# AI 에이전트에게 프롬프트를 제공하여 src/에 코드 생성
python3 exam_runner.py next      # 테스트 통과 후 다음 단계로
\`\`\`

Step 1 프롬프트는 \`prompts/step1.md\`에 있습니다. Step 2~8은 이전 단계 통과 후 자동 해제됩니다.

## 규칙

- **순서 엄수**: step1 → step2 → ... → step8 순서대로 진행
- **프롬프트만 참고**: \`prompts/stepN.md\` 요구사항만 보고 구현
- **이전 단계 수정 허용**: 후속 단계에서 이전 코드 수정 가능
- **한 세션 권장**: 같은 대화/세션에서 step1~8을 이어서 진행
SETREADME

    # --- exam_runner 빌드 (프롬프트 암호화 + Cython .so) ---
    $PYTHON "$SCRIPT_DIR/build_exam_runner.py" "$SCRIPT_DIR/$SET" "$TARGET" --no-compile
    $PYTHON -c "
import sys; sys.path.insert(0, '$SCRIPT_DIR')
from build_cython_tests import build_exam_runner_so
build_exam_runner_so('$TARGET/exam_runner.py', '$TARGET')
"

    # --- prompts/ 정리: step1.md만 남기고 step2~8 제거 ---
    for i in $(seq 2 8); do
        rm -f "$TARGET/prompts/step${i}.md"
    done

    echo "    완료"
done

# 응시자용 README
cp "$SCRIPT_DIR/candidate_README.md" "$ROOT_DIR/candidate-README.md"

echo ""
echo "  응시자용 완료."
echo ""

# ===========================
# 3. 결과 요약
# ===========================
echo "=== 빌드 완료 ==="
echo ""
echo "출력 디렉토리: $ROOT_DIR/"
echo ""
for L in $SETS; do
    echo "  candidate-${L}/  grader-${L}/"
done
echo ""
echo "Python 버전 요구사항: $PY_VERSION"
echo ""
echo "검증:"
echo "  cd $ROOT_DIR/grader-C && python3 -m pytest tests/ -v"
