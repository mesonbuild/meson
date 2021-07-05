# Copyright 2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file contains the detection logic for external dependencies that
# are UI-related.

import os
import typing as T

from .. import build
from ..mesonlib import relpath, HoldableObject
from ..interpreterbase.decorators import noKwargs, noPosargs

if T.TYPE_CHECKING:
    from ..interpreter import Interpreter
    from ..interpreterbase import TYPE_var, TYPE_kwargs
    from ..programs import ExternalProgram

class ModuleState:
    """Object passed to all module methods.

    This is a WIP API provided to modules, it should be extended to have everything
    needed so modules does not touch any other part of Meson internal APIs.
    """

    def __init__(self, interpreter: 'Interpreter') -> None:
        # Keep it private, it should be accessed only through methods.
        self._interpreter = interpreter

        self.source_root = interpreter.environment.get_source_dir()
        self.build_to_src = relpath(interpreter.environment.get_source_dir(),
                                    interpreter.environment.get_build_dir())
        self.subproject = interpreter.subproject
        self.subdir = interpreter.subdir
        self.current_lineno = interpreter.current_lineno
        self.environment = interpreter.environment
        self.project_name = interpreter.build.project_name
        self.project_version = interpreter.build.dep_manifest[interpreter.active_projectname]
        # The backend object is under-used right now, but we will need it:
        # https://github.com/mesonbuild/meson/issues/1419
        self.backend = interpreter.backend
        self.targets = interpreter.build.targets
        self.data = interpreter.build.data
        self.headers = interpreter.build.get_headers()
        self.man = interpreter.build.get_man()
        self.global_args = interpreter.build.global_args.host
        self.project_args = interpreter.build.projects_args.host.get(interpreter.subproject, {})
        self.build_machine = interpreter.builtin['build_machine'].held_object
        self.host_machine = interpreter.builtin['host_machine'].held_object
        self.target_machine = interpreter.builtin['target_machine'].held_object
        self.current_node = interpreter.current_node

    def get_include_args(self, include_dirs: T.Iterable[T.Union[str, build.IncludeDirs]], prefix: str = '-I') -> T.List[str]:
        if not include_dirs:
            return []

        srcdir = self.environment.get_source_dir()
        builddir = self.environment.get_build_dir()

        dirs_str: T.List[str] = []
        for dirs in include_dirs:
            if isinstance(dirs, str):
                dirs_str += [f'{prefix}{dirs}']
                continue

            # Should be build.IncludeDirs object.
            basedir = dirs.get_curdir()
            for d in dirs.get_incdirs():
                expdir = os.path.join(basedir, d)
                srctreedir = os.path.join(srcdir, expdir)
                buildtreedir = os.path.join(builddir, expdir)
                dirs_str += [f'{prefix}{buildtreedir}',
                             f'{prefix}{srctreedir}']
            for d in dirs.get_extra_build_dirs():
                dirs_str += [f'{prefix}{d}']

        return dirs_str

    def find_program(self, prog: T.Union[str, T.List[str]], required: bool = True,
                     version_func: T.Optional[T.Callable[['ExternalProgram'], str]] = None,
                     wanted: T.Optional[str] = None) -> 'ExternalProgram':
        return self._interpreter.find_program_impl(prog, required=required, version_func=version_func, wanted=wanted)


class ModuleObject(HoldableObject):
    """Base class for all objects returned by modules
    """
    def __init__(self) -> None:
        self.methods: T.Dict[
            str,
            T.Callable[[ModuleState, T.List['TYPE_var'], 'TYPE_kwargs'], T.Union[ModuleReturnValue, 'TYPE_var']]
        ] = {}


class MutableModuleObject(ModuleObject):
    pass


# FIXME: Port all modules to stop using self.interpreter and use API on
# ModuleState instead. Modules should stop using this class and instead use
# ModuleObject base class.
class ExtensionModule(ModuleObject):
    def __init__(self, interpreter: 'Interpreter') -> None:
        super().__init__()
        self.interpreter = interpreter
        self.methods.update({
            'found': self.found_method,
        })

    @noPosargs
    @noKwargs
    def found_method(self, state: 'ModuleState', args: T.List['TYPE_var'], kwargs: 'TYPE_kwargs') -> bool:
        return self.found()

    @staticmethod
    def found() -> bool:
        return True


class NewExtensionModule(ModuleObject):

    """Class for modern modules

    provides the found method.
    """

    def __init__(self) -> None:
        super().__init__()
        self.methods.update({
            'found': self.found_method,
        })

    @noPosargs
    @noKwargs
    def found_method(self, state: 'ModuleState', args: T.List['TYPE_var'], kwargs: 'TYPE_kwargs') -> bool:
        return self.found()

    @staticmethod
    def found() -> bool:
        return True


class NotFoundExtensionModule(NewExtensionModule):

    """Class for modern modules

    provides the found method.
    """

    @staticmethod
    def found() -> bool:
        return False


def is_module_library(fname):
    '''
    Check if the file is a library-like file generated by a module-specific
    target, such as GirTarget or TypelibTarget
    '''
    if hasattr(fname, 'fname'):
        fname = fname.fname
    suffix = fname.split('.')[-1]
    return suffix in ('gir', 'typelib')


class ModuleReturnValue:
    def __init__(self, return_value: T.Optional['TYPE_var'], new_objects: T.List['TYPE_var']) -> None:
        self.return_value = return_value
        assert(isinstance(new_objects, list))
        self.new_objects = new_objects

class GResourceTarget(build.CustomTarget):
    def __init__(self, name, subdir, subproject, kwargs):
        super().__init__(name, subdir, subproject, kwargs)

class GResourceHeaderTarget(build.CustomTarget):
    def __init__(self, name, subdir, subproject, kwargs):
        super().__init__(name, subdir, subproject, kwargs)

class GirTarget(build.CustomTarget):
    def __init__(self, name, subdir, subproject, kwargs):
        super().__init__(name, subdir, subproject, kwargs)

class TypelibTarget(build.CustomTarget):
    def __init__(self, name, subdir, subproject, kwargs):
        super().__init__(name, subdir, subproject, kwargs)

class VapiTarget(build.CustomTarget):
    def __init__(self, name, subdir, subproject, kwargs):
        super().__init__(name, subdir, subproject, kwargs)
