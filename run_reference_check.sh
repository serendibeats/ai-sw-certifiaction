#!/bin/bash
# 참조 구현 검증 스크립트 — reference-X/src/ 가 grader-X/tests/ 를 100% 통과하는지 확인
#
# 사용법:
#   ./run_reference_check.sh              # 전체 검증
#   ./run_reference_check.sh reference-C  # 특정 셋만

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

run_check() {
    local ref_dir=$1
    local letter=${ref_dir##*-}
    local grader_dir="grader-$letter"

    if [ ! -d "$SCRIPT_DIR/$ref_dir/src" ] || [ ! -d "$SCRIPT_DIR/$grader_dir/tests" ]; then
        echo "SKIP: $ref_dir or $grader_dir 없음"
        return
    fi

    echo "=== $ref_dir ==="
    # grader/src/ 대신 reference/src/ 를 사용하도록 심볼릭 링크로 교체
    local orig_src="$SCRIPT_DIR/$grader_dir/src"
    local backup_src="$SCRIPT_DIR/$grader_dir/src.bak"

    mv "$orig_src" "$backup_src"
    ln -s "$SCRIPT_DIR/$ref_dir/src" "$orig_src"

    cd "$SCRIPT_DIR/$grader_dir"
    python3 -m pytest tests/ -q --tb=short 2>&1 | tail -3

    # 복원
    rm "$orig_src"
    mv "$backup_src" "$orig_src"
    echo ""
}

cd "$SCRIPT_DIR"

if [ -n "$1" ]; then
    run_check "$1"
else
    for ref in reference-*/; do
        ref=${ref%/}
        run_check "$ref"
    done
fi
