#!/usr/bin/env python3
"""AI SW 역량 인증 시험 러너 — 단계별 프롬프트 잠금 시스템.

사용법:
    python3 exam_runner.py status          # 현재 진행 상태
    python3 exam_runner.py show            # 현재 단계 프롬프트 표시
    python3 exam_runner.py next            # 테스트 통과 확인 후 다음 단계로
    python3 exam_runner.py prev            # 이전 단계로 돌아가기
    python3 exam_runner.py test            # 현재 단계 테스트 실행
    python3 exam_runner.py test <N>        # 특정 단계 테스트 실행
"""
import base64
import glob
import json
import os
import subprocess
import sys
import zlib

# === 내장 프롬프트 데이터 (빌드 시 자동 생성) ===
# {step_number: base85_encoded_zlib_compressed_xor_encrypted_data}
PROMPTS = __PROMPTS_PLACEHOLDER__

TOTAL_STEPS = 8
STATE_FILE = ".exam_state.json"
XOR_KEY = b"ai-sw-cert-2025"


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _decode_prompt(encoded: str) -> str:
    raw = base64.b85decode(encoded)
    xored = _xor_bytes(raw, XOR_KEY)
    return zlib.decompress(xored).decode("utf-8")


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"current_step": 1, "passed_steps": []}


def _save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def _run_test(step: int) -> bool:
    test_file = f"tests/test_step{step}.py"
    if not os.path.exists(test_file):
        print(f"Error: {test_file} 파일이 없습니다.")
        return False
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
        capture_output=False,
    )
    return result.returncode == 0


def _get_prompt_content(step: int) -> str:
    encoded = PROMPTS.get(step)
    if encoded:
        return _decode_prompt(encoded)
    return None


def _clear_prompts():
    """prompts/ 디렉토리의 모든 step*.md 파일을 삭제합니다."""
    for f in glob.glob("prompts/step*.md"):
        os.remove(f)


def _set_current_prompt(step: int):
    """현재 단계의 프롬프트만 prompts/에 남깁니다."""
    _clear_prompts()
    content = _get_prompt_content(step)
    if content:
        os.makedirs("prompts", exist_ok=True)
        with open(f"prompts/step{step}.md", "w") as f:
            f.write(content)


def cmd_status():
    state = _load_state()
    step = state["current_step"]
    passed = state.get("passed_steps", [])
    print(f"=== 시험 진행 상태 ===")
    print()
    for i in range(1, TOTAL_STEPS + 1):
        if i in passed:
            mark = "[PASS]"
        elif i == step:
            mark = "[현재] ←"
        elif i < step:
            mark = "[미통과]"
        else:
            mark = "[잠금]"
        print(f"  Step {i}: {mark}")
    print()
    if step <= TOTAL_STEPS:
        print(f"다음 명령: python3 exam_runner.py show   (Step {step} 프롬프트 확인)")
    else:
        print("모든 단계를 완료했습니다!")


def cmd_show():
    state = _load_state()
    step = state["current_step"]

    if step > TOTAL_STEPS:
        print("모든 단계를 완료했습니다!")
        return

    content = _get_prompt_content(step)
    if content:
        # 프롬프트 파일이 없으면 생성
        prompt_path = f"prompts/step{step}.md"
        if not os.path.exists(prompt_path):
            _set_current_prompt(step)
        print(content)
    else:
        print(f"Error: Step {step} 프롬프트가 없습니다.")


def cmd_test(step: int = None):
    state = _load_state()
    if step is None:
        step = state["current_step"]
    print(f"=== Step {step} 테스트 실행 ===")
    print()
    passed = _run_test(step)
    if passed and step not in state.get("passed_steps", []):
        state.setdefault("passed_steps", []).append(step)
        _save_state(state)
    return passed


def cmd_next():
    state = _load_state()
    step = state["current_step"]

    if step > TOTAL_STEPS:
        print("모든 단계를 완료했습니다!")
        return

    # 이미 통과한 단계는 테스트 생략
    if step in state.get("passed_steps", []):
        print(f"Step {step}은 이미 통과했습니다. 다음 단계로 이동합니다.")
    else:
        # 현재 단계 테스트 실행
        print(f"=== Step {step} 테스트 확인 중... ===")
        print()
        passed = _run_test(step)

        if not passed:
            print()
            print(f"Step {step} 테스트를 통과하지 못했습니다.")
            print(f"프롬프트 확인: python3 exam_runner.py show")
            return

        # 통과 기록
        state.setdefault("passed_steps", []).append(step)

    next_step = step + 1
    state["current_step"] = next_step
    _save_state(state)

    print()
    if next_step > TOTAL_STEPS:
        _clear_prompts()
        print("=" * 50)
        print("모든 8단계를 완료했습니다!")
        print()
        print("최종 채점은 채점자에게 src/ 디렉토리를 제출하세요.")
        print("=" * 50)
    else:
        _set_current_prompt(next_step)
        content = _get_prompt_content(next_step)
        print("=" * 50)
        print(f"Step {next_step} 프롬프트가 해제되었습니다!")
        print(f"파일: prompts/step{next_step}.md")
        print("=" * 50)
        print()
        if content:
            print(content)


def cmd_prev():
    state = _load_state()
    step = state["current_step"]

    if step <= 1:
        print("이미 Step 1입니다. 더 이전 단계가 없습니다.")
        return

    prev_step = step - 1
    state["current_step"] = prev_step
    _save_state(state)

    _set_current_prompt(prev_step)
    print(f"Step {prev_step}로 돌아갔습니다.")
    print(f"파일: prompts/step{prev_step}.md")
    print()
    print(f"프롬프트 확인: python3 exam_runner.py show")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "status":
        cmd_status()
    elif cmd == "show":
        cmd_show()
    elif cmd == "test":
        step = int(sys.argv[2]) if len(sys.argv) > 2 else None
        cmd_test(step)
    elif cmd == "next":
        cmd_next()
    elif cmd == "prev":
        cmd_prev()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
