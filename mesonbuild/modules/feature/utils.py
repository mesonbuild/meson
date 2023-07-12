# Copyright (c) 2023, NumPy Developers.
# All rights reserved.

import typing as T
from ...mesonlib import MesonException, MachineChoice

if T.TYPE_CHECKING:
    from ...compilers import Compiler
    from ...mesonlib import File
    from .. import ModuleState

def get_compiler(state: 'ModuleState') -> 'Compiler':
    for_machine = MachineChoice.BUILD
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
              args: T.List[str], code: 'T.Union[str, File]'
              ) -> T.Tuple[bool, bool, str]:
    # TODO: treat warnings as errors
    with compiler.cached_compile(
        code, state.environment.coredata, extra_args=args
    ) as p:
        return p.cached, p.returncode == 0, p.stderr

