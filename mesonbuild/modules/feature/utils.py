# Copyright (c) 2023, NumPy Developers.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#
#     * Neither the name of the NumPy Developers nor the names of any
#        contributors may be used to endorse or promote products derived
#        from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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
              args: T.List[str], headers: T.List[str],
              code: 'T.Union[str, File]'
              ) -> T.Tuple[bool, bool, str]:
    if isinstance(code, str):
        heads = '\n'.join([f'#include <{h}>' for h in headers])
        code = heads + '\n' + code
    # TODO: treat warnings as errors
    with compiler.cached_compile(
        code, state.environment.coredata, extra_args=args
    ) as p:
        return p.cached, p.returncode == 0, p.stderr

