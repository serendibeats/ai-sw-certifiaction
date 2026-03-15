#!/bin/bash
# AI 코딩 에이전트 시험 실행 스크립트
#
# 사용법:
#   ./run_exam.sh <set-name>     # 시험 실행 (src/ 초기화 + 결과 수집)
#   ./run_exam.sh <set-name> -v  # 레퍼런스 검증 (src/ 유지)
#
# 예시:
#   ./run_exam.sh set-D          # set-D 시험 준비 (src/ 초기화)
#   ./run_exam.sh set-D -v       # set-D 레퍼런스 검증

SET_NAME=${1:-"set-D"}
MODE=${2:-"exam"}

if [ ! -d "$SET_NAME" ]; then
    echo "Error: '$SET_NAME' 디렉토리가 없습니다."
    echo "사용 가능: set-C, set-D, set-E, set-F"
    exit 1
fi

# 레퍼런스 검증 모드
if [ "$MODE" == "-v" ]; then
    echo "=== 레퍼런스 검증: $SET_NAME ==="
    cd "$SET_NAME"
    python3 -m pytest tests/ -v --tb=short 2>&1
    exit $?
fi

# 시험 모드: src/ 초기화
echo "=== 시험 준비: $SET_NAME ==="
echo ""
echo "다음 파일들의 내용이 초기화됩니다:"
ls "$SET_NAME/src/"*.py 2>/dev/null | grep -v __init__
echo ""
read -p "src/ 를 초기화하시겠습니까? (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "취소됨."
    exit 0
fi

cd "$SET_NAME/src"
for f in *.py; do
    if [ "$f" != "__init__.py" ]; then
        echo "" > "$f"
    fi
done
cd ../..

echo ""
echo "=== src/ 초기화 완료 ==="
echo ""
echo "이제 AI 에이전트에게 프롬프트를 순차적으로 제공하세요:"
echo ""
for i in $(seq 1 8); do
    if [ -f "$SET_NAME/prompts/step${i}.md" ]; then
        title=$(head -1 "$SET_NAME/prompts/step${i}.md" | sed 's/^#* *//')
        echo "  Step $i: $title"
    fi
done
echo ""
echo "모든 단계 완료 후 채점:"
echo "  python3 -m pytest $SET_NAME/tests/ -v"
echo "  python3 -m pytest $SET_NAME/tests/test_final.py -v  # 핵심"
