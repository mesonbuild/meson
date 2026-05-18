from __future__ import annotations

import typing as T
import tomllib

from ..mesonlib import MesonException


class CargoTomlError(MesonException):
    """Exception for TOML parsing errors, keeping proper location info."""


def load_toml(filename: str) -> T.Dict[str, object]:
    try:
        with open(filename, 'rb') as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        if hasattr(e, 'msg'):
            raise CargoTomlError(e.msg, file=filename, lineno=e.lineno, colno=e.colno) from e
        else:
            raise CargoTomlError(str(e), file=filename) from e
