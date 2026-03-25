#!/usr/bin/env python3
"""exam_runner.py 빌드 스크립트.

각 셋의 step1~8 프롬프트를 암호화하여 exam_runner.py에 내장하고,
.pyc로 컴파일합니다.

사용법:
    python3 build_exam_runner.py <set-dir> <output-dir>
    python3 build_exam_runner.py set-C dist/candidate-C
"""
import base64
import os
import py_compile
import sys
import zlib

XOR_KEY = b"ai-sw-cert-2025"


def xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def encode_prompt(text: str) -> str:
    compressed = zlib.compress(text.encode("utf-8"))
    xored = xor_bytes(compressed, XOR_KEY)
    return base64.b85encode(xored).decode("ascii")


def build_runner(set_dir: str, output_dir: str, no_compile: bool = False):
    # 원본 prompts에서 step1~8 읽기
    prompts = {}
    for step in range(1, 9):
        path = os.path.join(set_dir, "prompts", f"step{step}.md")
        if os.path.exists(path):
            with open(path) as f:
                prompts[step] = encode_prompt(f.read())

    # 템플릿 읽기
    template_path = os.path.join(os.path.dirname(__file__), "exam_runner_template.py")
    with open(template_path) as f:
        template = f.read()

    # PROMPTS 딕셔너리를 Python dict 리터럴로 생성
    prompt_lines = ["{\n"]
    for step, encoded in sorted(prompts.items()):
        prompt_lines.append(f"    {step}: {encoded!r},\n")
    prompt_lines.append("}")
    prompts_literal = "".join(prompt_lines)

    # 템플릿에 삽입
    runner_source = template.replace("__PROMPTS_PLACEHOLDER__", prompts_literal)

    # 출력
    runner_path = os.path.join(output_dir, "exam_runner.py")
    with open(runner_path, "w") as f:
        f.write(runner_source)

    if no_compile:
        # --no-compile: .py 소스만 생성, 컴파일은 외부에서 처리 (Cython 등)
        print(f"  exam_runner.py 소스 생성 완료 (컴파일 생략): {output_dir}")
        print(f"  내장 프롬프트: step {', '.join(str(s) for s in sorted(prompts.keys()))}")
        return

    # .pyc로 컴파일
    compiled_dir = os.path.join(output_dir, "_compiled")
    os.makedirs(compiled_dir, exist_ok=True)

    pyc_path = os.path.join(compiled_dir, "exam_runner.pyc")
    py_compile.compile(runner_path, cfile=pyc_path, doraise=True)

    # 원본 .py를 loader stub으로 교체
    with open(runner_path, "w") as f:
        f.write('''#!/usr/bin/env python3
"""AI SW 역량 인증 시험 러너."""
import importlib.util, pathlib, sys
_d = pathlib.Path(__file__).parent / "_compiled"
_s = importlib.util.spec_from_file_location(
    "__exam_runner__",
    next(_d.glob("exam_runner*.pyc")))
_m = importlib.util.module_from_spec(_s)
_s.loader.exec_module(_m)
if hasattr(_m, "main"):
    _m.main()
''')

    print(f"  exam_runner.py 생성 완료: {output_dir}")
    print(f"  내장 프롬프트: step {', '.join(str(s) for s in sorted(prompts.keys()))}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 build_exam_runner.py <set-dir> <output-dir> [--no-compile]")
        sys.exit(1)
    no_compile = "--no-compile" in sys.argv
    build_runner(sys.argv[1], sys.argv[2], no_compile=no_compile)
