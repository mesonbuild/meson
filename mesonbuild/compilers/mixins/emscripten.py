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
    from ..environment import Environment


class EmscriptenMixin:

    def _get_compile_output(self, dirname, mode):
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

    def get_options(self):
        opts = super().get_options()
        opts.update({
            '{}_thread_count'.format(self.language): coredata.UserIntegerOption(
                'Number of threads to use in web assembly, set to 0 to disable',
                (0, None, 4),  # Default was picked at random
            ),
        })

        return opts
