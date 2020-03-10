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

import typing as T
import os

from .. import build, mparser
from ..mesonlib import unholder, MesonException
from ..interpreter import InterpreterObject, ModuleState
from ..interpreterbase import flatten


class ModuleException(MesonException):
    pass

class ModuleObject(InterpreterObject):
    def __init__(self, interpreter):
        super().__init__()
        self.interpreter = interpreter

    def method_call(self, method_name: str,
                    args: T.List[T.Union[mparser.BaseNode, str, int, float, bool, list, dict, 'InterpreterObject', 'ObjectHolder']],
                    kwargs: T.Dict[str, T.Union[mparser.BaseNode, str, int, float, bool, list, dict, 'InterpreterObject', 'ObjectHolder']]):
        method = self.methods.get(method_name)
        if not method:
            raise InvalidCode('Unknown method "%s" in object.' % method_name)
        if not getattr(method, 'no-args-flattening', False):
            args = flatten(args)

        # This is not 100% reliable but we can't use hash()
        # because the Build object contains dicts and lists.
        num_targets = len(self.interpreter.build.targets)
        state = ModuleState(self.interpreter)
        ret = method(state, args, kwargs)
        if num_targets != len(self.interpreter.build.targets):
            raise ModuleException('Extension module altered internal state illegally.')

        if isinstance(ret, ModuleReturnValue):
            self.interpreter.process_new_values(ret.new_objects)
            ret = ret.return_value
        return self.interpreter.holderify(ret)

class ExtensionModule(ModuleObject):
    pass

def get_include_args(include_dirs, prefix='-I'):
    '''
    Expand include arguments to refer to the source and build dirs
    by using @SOURCE_ROOT@ and @BUILD_ROOT@ for later substitution
    '''
    if not include_dirs:
        return []

    dirs_str = []
    for dirs in unholder(include_dirs):
        if isinstance(dirs, str):
            dirs_str += ['%s%s' % (prefix, dirs)]
            continue

        # Should be build.IncludeDirs object.
        basedir = dirs.get_curdir()
        for d in dirs.get_incdirs():
            expdir = os.path.join(basedir, d)
            srctreedir = os.path.join('@SOURCE_ROOT@', expdir)
            buildtreedir = os.path.join('@BUILD_ROOT@', expdir)
            dirs_str += ['%s%s' % (prefix, buildtreedir),
                         '%s%s' % (prefix, srctreedir)]
        for d in dirs.get_extra_build_dirs():
            dirs_str += ['%s%s' % (prefix, d)]

    return dirs_str

class ModuleReturnValue:
    def __init__(self, return_value, new_objects):
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
