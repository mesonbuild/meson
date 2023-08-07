# Copyright (c) 2023, NumPy Developers.
# All rights reserved.
#

import typing as T

from .module import Module

if T.TYPE_CHECKING:
    from ...interpreter import Interpreter

def initialize(interpreter: 'Interpreter') -> Module:
    return Module()
