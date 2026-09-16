# Copyright (c) 2023, NumPy Developers.
import hashlib
from typing import Tuple, List, Union, Any, TYPE_CHECKING
from ...mesonlib import MesonException, MachineChoice
from ...compilers.compilers import CompileCheckMode, Compiler

if TYPE_CHECKING:
    from ...mesonlib import File
    from .. import ModuleState

def get_compiler(state: 'ModuleState') -> 'Compiler':
    for_machine = MachineChoice.HOST
    clist = state.environment.coredata.compilers[for_machine]
    for cstr in ('c', 'cpp'):
        try:
            compiler = clist[cstr]
            break
        except KeyError:
            raise MesonException(
                'Unable to get compiler for C or C++ language '
                'try to specify a valid C/C++ compiler via option "compiler".'
            )
    return compiler

def test_code(state: 'ModuleState', compiler: 'Compiler',
              args: List[str], code: 'Union[str, File]'
              ) -> Tuple[bool, bool, str]:
    # TODO: Add option to treat warnings as errors
    with compiler.cached_compile(
        code, extra_args=args, mode=CompileCheckMode.COMPILE
    ) as p:
        return p.cached, p.returncode == 0, p.stderr

def generate_hash(*args: Any) -> str:
    hasher = hashlib.sha1()
    for a in args:
        hasher.update(bytes(str(a), encoding='utf-8'))
    return hasher.hexdigest()
