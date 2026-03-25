#!/usr/bin/env python3
"""AI SW 역량 인증 시험 러너 — 단계별 프롬프트 잠금 시스템.

사용법:
    python3 exam_runner.py status          # 현재 진행 상태
    python3 exam_runner.py show            # 현재 단계 프롬프트 표시
    python3 exam_runner.py next            # 테스트 통과 확인 후 다음 단계로
    python3 exam_runner.py test            # 현재 단계 테스트 실행
    python3 exam_runner.py test <N>        # 특정 단계 테스트 실행
"""
import base64
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


def _save_prompt_file(step: int, content: str):
    os.makedirs("prompts", exist_ok=True)
    path = f"prompts/step{step}.md"
    with open(path, "w") as f:
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


def cmd_show(step: int = None):
    state = _load_state()
    if step is None:
        step = state["current_step"]

    if step > TOTAL_STEPS:
        print("모든 단계를 완료했습니다!")
        return

    if step > state["current_step"]:
        print(f"Error: Step {step}은 아직 잠겨있습니다. 현재 Step {state['current_step']}입니다.")
        return

    if step == 1:
        # Step 1은 prompts/step1.md에서 직접 읽기
        path = "prompts/step1.md"
        if os.path.exists(path):
            with open(path) as f:
                print(f.read())
        else:
            print("Error: prompts/step1.md 파일이 없습니다.")
    else:
        encoded = PROMPTS.get(step)
        if encoded:
            content = _decode_prompt(encoded)
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
    if step not in state.get("passed_steps", []):
        state.setdefault("passed_steps", []).append(step)

    next_step = step + 1
    state["current_step"] = next_step
    _save_state(state)

    print()
    if next_step > TOTAL_STEPS:
        print("=" * 50)
        print("모든 8단계를 완료했습니다!")
        print()
        print("최종 채점은 채점자에게 src/ 디렉토리를 제출하세요.")
        print("=" * 50)
    else:
        # 다음 프롬프트를 파일로 저장하고 표시
        encoded = PROMPTS.get(next_step)
        if encoded:
            content = _decode_prompt(encoded)
            _save_prompt_file(next_step, content)
            print("=" * 50)
            print(f"Step {next_step} 프롬프트가 해제되었습니다!")
            print(f"파일: prompts/step{next_step}.md")
            print("=" * 50)
            print()
            print(content)
        else:
            print(f"Error: Step {next_step} 프롬프트가 없습니다.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "status":
        cmd_status()
    elif cmd == "show":
        step = int(sys.argv[2]) if len(sys.argv) > 2 else None
        cmd_show(step)
    elif cmd == "test":
        step = int(sys.argv[2]) if len(sys.argv) > 2 else None
        cmd_test(step)
    elif cmd == "next":
        cmd_next()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
