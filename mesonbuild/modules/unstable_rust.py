# Copyright © 2020 Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import typing as T

from . import ExtensionModule, ModuleReturnValue
from .. import mlog
from ..build import BuildTarget, Executable, InvalidArguments
from ..dependencies import Dependency, ExternalLibrary
from ..interpreter import ExecutableHolder, permitted_kwargs
from ..interpreterbase import InterpreterException, permittedKwargs, FeatureNew
from ..mesonlib import stringlistify, unholder, listify

if T.TYPE_CHECKING:
    from ..interpreter import ModuleState, Interpreter


class RustModule(ExtensionModule):

    """A module that holds helper functions for rust."""

    @FeatureNew('rust module', '0.57.0')
    def __init__(self, interpreter: 'Interpreter') -> None:
        super().__init__(interpreter)

    @permittedKwargs(permitted_kwargs['test'] | {'dependencies'} ^ {'protocol'})
    def test(self, state: 'ModuleState', args: T.List, kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        """Generate a rust test target from a given rust target.

        Rust puts it's unitests inside it's main source files, unlike most
        languages that put them in external files. This means that normally
        you have to define two separate targets with basically the same
        arguments to get tests:

        ```meson
        rust_lib_sources = [...]
        rust_lib = static_library(
            'rust_lib',
            rust_lib_sources,
        )

        rust_lib_test = executable(
            'rust_lib_test',
            rust_lib_sources,
            rust_args : ['--test'],
        )

        test(
            'rust_lib_test',
            rust_lib_test,
            protocol : 'rust',
        )
        ```

        This is all fine, but not very DRY. This method makes it much easier
        to define rust tests:

        ```meson
        rust = import('unstable-rust')

        rust_lib = static_library(
            'rust_lib',
            [sources],
        )

        rust.test('rust_lib_test', rust_lib)
        ```
        """
        if len(args) != 2:
            raise InterpreterException('rustmod.test() takes exactly 2 positional arguments')
        name: str = args[0]
        if not isinstance(name, str):
            raise InterpreterException('First positional argument to rustmod.test() must be a string')
        base_target: BuildTarget = unholder(args[1])
        if not isinstance(base_target, BuildTarget):
            raise InterpreterException('Second positional argument to rustmod.test() must be a library or executable')
        if not base_target.uses_rust():
            raise InterpreterException('Second positional argument to rustmod.test() must be a rust based target')
        extra_args = stringlistify(kwargs.get('args', []))

        # Delete any arguments we don't want passed
        if '--test' in extra_args:
            mlog.warning('Do not add --test to rustmod.test arguments')
            extra_args.remove('--test')
        if '--format' in extra_args:
            mlog.warning('Do not add --format to rustmod.test arguments')
            i = extra_args.index('--format')
            # Also delete the argument to --format
            del extra_args[i + 1]
            del extra_args[i]
        for i, a in enumerate(extra_args):
            if a.startswith('--format='):
                del extra_args[i]
                break

        dependencies = unholder(listify(kwargs.get('dependencies', [])))
        for d in dependencies:
            if not isinstance(d, (Dependency, ExternalLibrary)):
                raise InvalidArguments('dependencies must be a dependency or external library')

        kwargs['args'] = extra_args + ['--test', '--format', 'pretty']
        kwargs['protocol'] = 'rust'

        new_target_kwargs = base_target.kwargs.copy()
        # Don't mutate the shallow copied list, instead replace it with a new
        # one
        new_target_kwargs['rust_args'] = new_target_kwargs.get('rust_args', []) + ['--test']
        new_target_kwargs['install'] = False
        new_target_kwargs['dependencies'] = new_target_kwargs.get('dependencies', []) + dependencies

        new_target = Executable(
            name, base_target.subdir, state.subproject,
            base_target.for_machine, base_target.sources,
            base_target.objects, base_target.environment,
            new_target_kwargs
        )

        e = ExecutableHolder(new_target, self.interpreter)
        test = self.interpreter.make_test(
            self.interpreter.current_node, [name, e], kwargs)

        return ModuleReturnValue([], [e, test])


def initialize(*args: T.List, **kwargs: T.Dict) -> RustModule:
    return RustModule(*args, **kwargs)  # type: ignore
