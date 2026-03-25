"""Compiled test module — native binary."""
import importlib.util, importlib.machinery, pathlib

_d = pathlib.Path(__file__).parent / "_compiled"
_ext = importlib.machinery.EXTENSION_SUFFIXES[0]
_so = _d / (pathlib.Path(__file__).stem + _ext)
if not _so.exists():
    raise ImportError(f"Compiled test not found: {_so}")
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
        _methods = {}
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
