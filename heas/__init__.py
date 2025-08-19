# heas/__init__.py
from .api import optimize, simulate, evaluate
__all__ = ["optimize", "simulate", "evaluate"]

# Avoid hard-coding: read version from installed metadata
try:
    from importlib.metadata import version as _pkg_version, PackageNotFoundError
except Exception:  # Py<3.8 backport if you ever need it
    try:
        from importlib_metadata import version as _pkg_version, PackageNotFoundError  # type: ignore
    except Exception:
        _pkg_version = None
        class PackageNotFoundError(Exception): ...
try:
    __version__ = _pkg_version("heas") if _pkg_version else "0.0.0"
except PackageNotFoundError:
    __version__ = "0.0.0"