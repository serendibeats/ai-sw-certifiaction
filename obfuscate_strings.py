#!/usr/bin/env python3
"""AST-based string/number literal obfuscation for Python test files.

Replaces string and numeric literals in Python source with XOR-decoded
runtime calls, so that `strings` on the compiled .so reveals nothing useful.

Usage:
    python3 obfuscate_strings.py input.py output.py
    python3 obfuscate_strings.py input_dir/ output_dir/   # batch mode
"""
import ast
import os
import random
import struct
import sys
import textwrap

# XOR key for obfuscation (randomized per build for extra safety)
DEFAULT_KEY = 0xA7

# Literals shorter than this are not worth obfuscating
MIN_STR_LEN = 1

# Names/patterns to skip (imports, decorators, docstrings handled separately)
_SKIP_FUNC_NAMES = {"pytest.raises", "raises"}


def xor_encode_str(s: str, key: int = DEFAULT_KEY) -> bytes:
    """XOR-encode a string, return the encoded bytes."""
    raw = s.encode("utf-8")
    return bytes(b ^ key for b in raw)


def xor_encode_float(f: float, key: int = DEFAULT_KEY) -> bytes:
    """XOR-encode a float (as 8-byte double), return encoded bytes."""
    raw = struct.pack("d", f)
    return bytes(b ^ key for b in raw)


def xor_encode_int(n: int, key: int = DEFAULT_KEY) -> bytes:
    """XOR-encode an integer (as 8-byte signed long), return encoded bytes."""
    raw = struct.pack("q", n)
    return bytes(b ^ key for b in raw)


def _bytes_literal(data: bytes) -> str:
    """Convert bytes to a Python bytes literal string."""
    return repr(data)


class _LiteralObfuscator(ast.NodeTransformer):
    """AST transformer that replaces string/number constants with decode calls."""

    def __init__(self, key: int = DEFAULT_KEY):
        self.key = key
        self._in_import = False
        self._in_decorator = False
        self._func_depth = 0
        self._first_expr_in_func = False

    def visit_Import(self, node):
        self._in_import = True
        self.generic_visit(node)
        self._in_import = False
        return node

    def visit_ImportFrom(self, node):
        self._in_import = True
        self.generic_visit(node)
        self._in_import = False
        return node

    def visit_JoinedStr(self, node):
        """Skip f-string internals — ast.unparse() can't handle Call nodes inside."""
        return node

    def visit_FunctionDef(self, node):
        """Track function entry to skip docstrings."""
        self._func_depth += 1
        # Check if first statement is a docstring
        old_first = self._first_expr_in_func
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            # Skip the docstring — replace with empty string or leave as is
            # We'll just skip obfuscating it
            pass
        self.generic_visit(node)
        self._func_depth -= 1
        self._first_expr_in_func = old_first
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        """Track class entry to skip docstrings."""
        self.generic_visit(node)
        return node

    def _is_docstring(self, node):
        """Check if a Constant node is likely a docstring."""
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            return False
        # A docstring is the first expression statement in a module/class/function
        # We handle this by checking parent context
        return False

    def _should_skip_constant(self, node):
        """Determine if this constant should NOT be obfuscated."""
        if self._in_import:
            return True
        if self._in_decorator:
            return True
        return False

    def visit_Constant(self, node):
        if self._should_skip_constant(node):
            return node

        val = node.value

        # String literals
        if isinstance(val, str):
            # Skip empty strings and very short ones, and docstrings (triple-quoted)
            if len(val) < MIN_STR_LEN:
                return node
            # Skip format strings that are just markers
            if val in ("", "\n"):
                return node

            encoded = xor_encode_str(val, self.key)
            # _ds(b'...') -> decode string
            return ast.Call(
                func=ast.Name(id="_ds", ctx=ast.Load()),
                args=[ast.Constant(value=encoded)],
                keywords=[],
            )

        # Float literals
        if isinstance(val, float):
            encoded = xor_encode_float(val, self.key)
            return ast.Call(
                func=ast.Name(id="_df", ctx=ast.Load()),
                args=[ast.Constant(value=encoded)],
                keywords=[],
            )

        # Integer literals (skip 0, 1, -1 and small values used for indexing)
        if isinstance(val, int) and not isinstance(val, bool):
            if abs(val) <= 2:
                return node
            encoded = xor_encode_int(val, self.key)
            return ast.Call(
                func=ast.Name(id="_di", ctx=ast.Load()),
                args=[ast.Constant(value=encoded)],
                keywords=[],
            )

        return node


def _decoder_header(key: int = DEFAULT_KEY) -> str:
    """Generate the runtime decoder functions to prepend to source."""
    return textwrap.dedent(f"""\
        import struct as _struct
        def _ds(_b):
            return bytes(b ^ {key} for b in _b).decode("utf-8")
        def _df(_b):
            return _struct.unpack("d", bytes(b ^ {key} for b in _b))[0]
        def _di(_b):
            return _struct.unpack("q", bytes(b ^ {key} for b in _b))[0]
    """)


def obfuscate_source(source: str, key: int = DEFAULT_KEY) -> str:
    """Obfuscate string/number literals in Python source code.

    Returns the transformed source with decoder functions prepended.
    """
    tree = ast.parse(source)

    # Find and preserve the module docstring
    module_docstring = None
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)):
        module_docstring = tree.body[0].value.value
        # Remove docstring from tree so transformer doesn't touch it
        tree.body = tree.body[1:]

    # Find and preserve function/method docstrings
    _mark_docstrings(tree)

    # Transform
    transformer = _LiteralObfuscator(key)
    tree = transformer.visit(tree)
    ast.fix_missing_locations(tree)

    # Unparse back to source
    result = ast.unparse(tree)

    # Prepend cython directive, decoder functions, and docstring
    parts = []
    parts.append("# cython: binding=True")
    if module_docstring:
        parts.append(f'"""{module_docstring}"""')
    parts.append(_decoder_header(key))
    parts.append(result)

    return "\n".join(parts)


def _mark_docstrings(tree):
    """Mark docstring nodes so the transformer skips them."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                # Mark it by replacing with a pass statement
                # (docstrings in test files are not important)
                node.body[0] = ast.Pass()


def obfuscate_file(input_path: str, output_path: str, key: int = DEFAULT_KEY):
    """Obfuscate a single Python file."""
    with open(input_path) as f:
        source = f.read()

    result = obfuscate_source(source, key)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(result)


def obfuscate_directory(input_dir: str, output_dir: str, pattern: str = "test_step*.py",
                        key: int = DEFAULT_KEY):
    """Obfuscate all matching files in a directory."""
    import glob
    files = glob.glob(os.path.join(input_dir, pattern))
    for fpath in sorted(files):
        fname = os.path.basename(fpath)
        out = os.path.join(output_dir, fname)
        obfuscate_file(fpath, out, key)
        print(f"  난독화: {fname}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 obfuscate_strings.py <input> <output> [key]")
        print("  input/output: file or directory")
        sys.exit(1)

    inp, out = sys.argv[1], sys.argv[2]
    key = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_KEY

    if os.path.isdir(inp):
        obfuscate_directory(inp, out, key=key)
    else:
        obfuscate_file(inp, out, key=key)
        print(f"완료: {out}")
