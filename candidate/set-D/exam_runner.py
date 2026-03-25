#!/usr/bin/env python3
"""AI SW 역량 인증 시험 러너."""
import importlib.util, importlib.machinery, pathlib, sys
_d = pathlib.Path(__file__).parent / "_compiled"
_ext = importlib.machinery.EXTENSION_SUFFIXES[0]
_so = _d / ("exam_runner" + _ext)
if not _so.exists():
    raise ImportError(f"Compiled runner not found: {_so}")
_s = importlib.util.spec_from_file_location("exam_runner", str(_so))
_m = importlib.util.module_from_spec(_s)
_s.loader.exec_module(_m)
if hasattr(_m, "main"):
    _m.main()
