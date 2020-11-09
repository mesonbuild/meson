# Copyright 2019 The meson development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Provides a mixin for shared code between C and C++ Emscripten compilers."""

import os.path
import typing as T

from ... import coredata

if T.TYPE_CHECKING:
    from ...environment import Environment
    from ...compilers.compilers import Compiler
else:
    # This is a bit clever, for mypy we pretend that these mixins descend from
    # Compiler, so we get all of the methods and attributes defined for us, but
    # for runtime we make them descend from object (which all classes normally
    # do). This gives up DRYer type checking, with no runtime impact
    Compiler = object


class EmscriptenMixin(Compiler):

    def _get_compile_output(self, dirname: str, mode: str) -> str:
        # In pre-processor mode, the output is sent to stdout and discarded
        if mode == 'preprocess':
            return None
        # Unlike sane toolchains, emcc infers the kind of output from its name.
        # This is the only reason why this method is overridden; compiler tests
        # do not work well with the default exe/obj suffices.
        if mode == 'link':
            suffix = 'js'
        else:
            suffix = 'wasm'
        return os.path.join(dirname, 'output.' + suffix)

    def thread_flags(self, env: 'Environment') -> T.List[str]:
        return ['-s', 'USE_PTHREADS=1']

    def thread_link_flags(self, env: 'Environment') -> T.List[str]:
        args = ['-s', 'USE_PTHREADS=1']
        count = env.coredata.compiler_options[self.for_machine][self.language]['thread_count'].value  # type: int
        if count:
            args.extend(['-s', 'PTHREAD_POOL_SIZE={}'.format(count)])
        return args

    def get_options(self) -> 'coredata.OptionDictType':
        opts = super().get_options()
        opts.update({
            'thread_count': coredata.UserIntegerOption(
                'Number of threads to use in web assembly, set to 0 to disable',
                (0, None, 4),  # Default was picked at random
            ),
        })

        return opts
