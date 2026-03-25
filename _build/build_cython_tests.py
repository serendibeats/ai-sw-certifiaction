#!/usr/bin/env python3
"""Cython-based test compilation pipeline.

Takes test .py files, obfuscates string literals, compiles to native .so
via Cython, and generates pytest-compatible loader stubs.

Usage:
    python3 build_cython_tests.py <set-tests-dir> <output-tests-dir>
    python3 build_cython_tests.py set-C/tests/ dist/candidate/set-C/tests/

Requires: cython, a C compiler (gcc/clang), python3-dev headers
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from obfuscate_strings import obfuscate_file

# XOR key for this build (could be randomized per build)
OBF_KEY = 0xA7


def _get_so_suffix():
    """Get the platform-specific .so suffix (e.g., .cpython-312-x86_64-linux-gnu.so)."""
    import importlib.machinery
    return importlib.machinery.EXTENSION_SUFFIXES[0]


def compile_test_to_so(py_path: str, output_dir: str, key: int = OBF_KEY) -> str:
    """Compile a single test .py file to a .so via Cython.

    Steps:
    1. Obfuscate string literals
    2. Cythonize to .c
    3. Compile .c to .so

    Returns the path to the generated .so file.
    """
    basename = os.path.splitext(os.path.basename(py_path))[0]

    with tempfile.TemporaryDirectory(prefix="cython_build_") as tmpdir:
        # Step 1: Obfuscate
        obf_path = os.path.join(tmpdir, f"{basename}.py")
        obfuscate_file(py_path, obf_path, key)

        # Step 2: Cythonize (.py -> .c)
        result = subprocess.run(
            [sys.executable, "-m", "cython", "-X", "binding=True", obf_path],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  Cython ERROR for {basename}: {result.stderr}", file=sys.stderr)
            raise RuntimeError(f"Cython compilation failed for {basename}")

        c_path = os.path.join(tmpdir, f"{basename}.c")
        if not os.path.exists(c_path):
            raise RuntimeError(f"Cython did not produce {c_path}")

        # Step 3: Compile .c -> .so
        so_suffix = _get_so_suffix()
        so_name = f"{basename}{so_suffix}"
        so_path = os.path.join(tmpdir, so_name)

        # Get Python include path
        import sysconfig
        include = sysconfig.get_path("include")
        ldflags = sysconfig.get_config_var("LDSHARED") or "gcc -shared"

        compile_cmd = [
            "gcc",
            "-shared", "-fPIC",
            "-O2",
            f"-I{include}",
            "-o", so_path,
            c_path,
        ]

        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  GCC ERROR for {basename}: {result.stderr}", file=sys.stderr)
            raise RuntimeError(f"C compilation failed for {basename}")

        # Step 4: Copy .so to output
        os.makedirs(output_dir, exist_ok=True)
        final_so = os.path.join(output_dir, so_name)
        shutil.copy2(so_path, final_so)

        return final_so


def generate_loader_stub(test_name: str, compiled_dir_name: str = "_compiled") -> str:
    """Generate a pytest-compatible loader stub that imports from the .so file.

    Creates Python wrapper classes/functions around Cython-compiled code
    so that pytest's inspect.isfunction() check passes.
    """
    return f'''"""Compiled test module — native binary."""
import importlib.util, importlib.machinery, pathlib

_d = pathlib.Path(__file__).parent / "{compiled_dir_name}"
_ext = importlib.machinery.EXTENSION_SUFFIXES[0]
_so = _d / (pathlib.Path(__file__).stem + _ext)
if not _so.exists():
    raise ImportError(f"Compiled test not found: {{_so}}")
_s = importlib.util.spec_from_file_location(__name__, str(_so))
_m = importlib.util.module_from_spec(_s)
_s.loader.exec_module(_m)

def _wrap(fn):
    """Create a real Python function wrapper for a Cython function."""
    def wrapper(*a, **kw):
        return fn(*a, **kw)
    wrapper.__name__ = getattr(fn, "__name__", "unknown")
    wrapper.__qualname__ = getattr(fn, "__qualname__", wrapper.__name__)
    return wrapper

for _n in dir(_m):
    _obj = getattr(_m, _n)
    if _n.startswith("Test") and isinstance(_obj, type):
        # Wrap test class: create a Python class with Python-function methods
        # Include ALL non-dunder methods (test_, setup_, teardown_, _helpers)
        _methods = {{}}
        for _mn in dir(_obj):
            if _mn.startswith("__"):
                continue
            _attr = getattr(_obj, _mn)
            if callable(_attr):
                _methods[_mn] = _wrap(_attr)
        globals()[_n] = type(_n, (), _methods)
    elif _n.startswith("test_") and callable(_obj):
        globals()[_n] = _wrap(_obj)
    elif _n.startswith("_") and not _n.startswith("__") and callable(_obj):
        # Helper functions like _setup(), _full_setup()
        globals()[_n] = _obj
'''


def build_tests(source_tests_dir: str, output_tests_dir: str, key: int = OBF_KEY):
    """Build all test_step*.py files in a directory to .so binaries.

    Creates:
      output_tests_dir/
        test_step1.py           # loader stub
        test_step2.py           # loader stub
        ...
        _compiled/
          test_step1.cpython-312-x86_64-linux-gnu.so
          test_step2.cpython-312-x86_64-linux-gnu.so
          ...
    """
    compiled_dir = os.path.join(output_tests_dir, "_compiled")
    os.makedirs(compiled_dir, exist_ok=True)

    test_files = sorted(glob.glob(os.path.join(source_tests_dir, "test_step*.py")))

    if not test_files:
        print(f"  WARNING: No test_step*.py files found in {source_tests_dir}")
        return

    for test_file in test_files:
        basename = os.path.splitext(os.path.basename(test_file))[0]
        print(f"  컴파일: {basename}")

        # Compile to .so
        so_path = compile_test_to_so(test_file, compiled_dir, key)

        # Generate loader stub
        stub_path = os.path.join(output_tests_dir, f"{basename}.py")
        with open(stub_path, "w") as f:
            f.write(generate_loader_stub(basename))

    print(f"  .so 파일: {compiled_dir}")


def build_exam_runner_so(source_runner: str, output_dir: str, key: int = OBF_KEY):
    """Compile exam_runner.py to .so as well."""
    compiled_dir = os.path.join(output_dir, "_compiled")
    so_path = compile_test_to_so(source_runner, compiled_dir, key)
    basename = "exam_runner"

    stub_path = os.path.join(output_dir, f"{basename}.py")
    with open(stub_path, "w") as f:
        f.write(f'''#!/usr/bin/env python3
"""AI SW 역량 인증 시험 러너."""
import importlib.util, importlib.machinery, pathlib, sys
_d = pathlib.Path(__file__).parent / "_compiled"
_ext = importlib.machinery.EXTENSION_SUFFIXES[0]
_so = _d / ("exam_runner" + _ext)
if not _so.exists():
    raise ImportError(f"Compiled runner not found: {{_so}}")
_s = importlib.util.spec_from_file_location("exam_runner", str(_so))
_m = importlib.util.module_from_spec(_s)
_s.loader.exec_module(_m)
if hasattr(_m, "main"):
    _m.main()
''')

    return so_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 build_cython_tests.py <source-tests-dir> <output-tests-dir>")
        sys.exit(1)

    build_tests(sys.argv[1], sys.argv[2])
