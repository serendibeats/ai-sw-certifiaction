#!/bin/bash
# AI SW 역량 인증 시험 — 채점 스크립트
#
# 사용법:
#   ./run_grading.sh <grader-dir> <candidate-src-dir>
#
# 예시:
#   ./run_grading.sh grader-C candidate-C/src/
#   ./run_grading.sh grader-D candidate-D/src/

SET_NAME=${1:-""}
SUBMISSION_DIR=${2:-""}

if [ -z "$SET_NAME" ] || [ -z "$SUBMISSION_DIR" ]; then
    echo "사용법: ./run_grading.sh <grader-dir> <candidate-src-dir>"
    echo ""
    echo "예시:"
    echo "  ./run_grading.sh grader-C candidate-C/src/"
    echo "  ./run_grading.sh grader-D candidate-D/src/"
    exit 1
fi

if [ ! -d "$SET_NAME" ]; then
    echo "Error: '$SET_NAME' 디렉토리가 없습니다."
    exit 1
fi

if [ ! -d "$SUBMISSION_DIR" ]; then
    echo "Error: '$SUBMISSION_DIR' 디렉토리가 없습니다."
    exit 1
fi

# 채점 후 grader/src/ 정리 (정상/비정상 종료 모두)
cleanup() {
    for f in "$SET_NAME/src/"*.py; do
        fname=$(basename "$f")
        if [ "$fname" != "__init__.py" ]; then
            rm -f "$f"
        fi
    done
}
trap cleanup EXIT

# 응시자 제출물을 grader/src/에 복사
echo "=== 채점: $SET_NAME ==="
echo "제출물: $SUBMISSION_DIR"
echo ""

for f in "$SUBMISSION_DIR/"*.py; do
    [ ! -f "$f" ] && continue
    fname=$(basename "$f")
    [ "$fname" = "__init__.py" ] && continue
    cp "$f" "$SET_NAME/src/$fname"
done

echo "--- 전체 테스트 ---"
echo ""
FULL_OUTPUT=$(cd "$SET_NAME" && python3 -m pytest tests/ -v --tb=short 2>&1)
echo "$FULL_OUTPUT"

echo ""
echo "--- 통합 테스트 (test_final.py) ---"
echo ""
FINAL_OUTPUT=$(cd "$SET_NAME" && python3 -m pytest tests/test_final.py -v --tb=short 2>&1)
echo "$FINAL_OUTPUT"

# 등급 산출
PASSED=$(echo "$FINAL_OUTPUT" | grep -oP '\d+(?= passed)' || echo "0")
FAILED=$(echo "$FINAL_OUTPUT" | grep -oP '\d+(?= failed)' || echo "0")
ERRORS=$(echo "$FINAL_OUTPUT" | grep -oP '\d+(?= error)' || echo "0")

# 빈 문자열 처리
PASSED=${PASSED:-0}
FAILED=${FAILED:-0}
ERRORS=${ERRORS:-0}

TOTAL=$((PASSED + FAILED + ERRORS))

if [ "$TOTAL" -gt 0 ]; then
    RATE=$((PASSED * 100 / TOTAL))
else
    RATE=0
fi

echo ""
echo "=== 채점 결과 ==="
echo ""
echo "test_final: $PASSED/$TOTAL passed ($RATE%)"

if [ "$RATE" -ge 90 ]; then
    GRADE="A"
    DESC="우수 — 구조적 리팩토링 능력 입증"
elif [ "$RATE" -ge 75 ]; then
    GRADE="B"
    DESC="양호 — 대부분의 통합 시나리오 처리"
elif [ "$RATE" -ge 60 ]; then
    GRADE="C"
    DESC="보통 — 일부 cross-cutting concern 누락"
elif [ "$RATE" -ge 40 ]; then
    GRADE="D"
    DESC="미흡 — 주요 구조 변경 실패"
else
    GRADE="F"
    DESC="불합격 — 심각한 스파게티 코드 발생"
fi

echo "등급: $GRADE ($DESC)"
