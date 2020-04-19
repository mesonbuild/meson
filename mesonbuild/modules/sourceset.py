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

from collections import namedtuple
from .. import mesonlib
from ..mesonlib import listify
from . import ExtensionModule
from ..interpreterbase import (
    noPosargs, noKwargs, permittedKwargs,
    InterpreterObject, MutableInterpreterObject, ObjectHolder,
    InterpreterException, InvalidArguments, InvalidCode, FeatureNew,
)
from ..interpreter import (
    GeneratedListHolder, CustomTargetHolder,
    CustomTargetIndexHolder
)

SourceSetRule = namedtuple('SourceSetRule', 'keys sources if_false sourcesets dependencies extra_deps')
SourceFiles = namedtuple('SourceFiles', 'sources dependencies')

class SourceSetHolder(MutableInterpreterObject, ObjectHolder):
    def __init__(self, interpreter):
        MutableInterpreterObject.__init__(self)
        ObjectHolder.__init__(self, list())
        self.subproject = interpreter.subproject
        self.environment = interpreter.environment
        self.subdir = interpreter.subdir
        self.frozen = False
        self.methods.update({
            'add': self.add_method,
            'add_all': self.add_all_method,
            'all_sources': self.all_sources_method,
            'all_dependencies': self.all_dependencies_method,
            'apply': self.apply_method,
        })

    def check_source_files(self, arg, allow_deps):
        sources = []
        deps = []
        for x in arg:
            if isinstance(x, (str, mesonlib.File,
                              GeneratedListHolder, CustomTargetHolder,
                              CustomTargetIndexHolder)):
                sources.append(x)
            elif hasattr(x, 'found'):
                if not allow_deps:
                    msg = 'Dependencies are not allowed in the if_false argument.'
                    raise InvalidArguments(msg)
                deps.append(x)
            else:
                msg = 'Sources must be strings or file-like objects.'
                raise InvalidArguments(msg)
        mesonlib.check_direntry_issues(sources)
        return sources, deps

    def check_conditions(self, arg):
        keys = []
        deps = []
        for x in listify(arg):
            if isinstance(x, str):
                keys.append(x)
            elif hasattr(x, 'found'):
                deps.append(x)
            else:
                raise InvalidArguments('Conditions must be strings or dependency object')
        return keys, deps

    @permittedKwargs(['when', 'if_false', 'if_true'])
    def add_method(self, args, kwargs):
        if self.frozen:
            raise InvalidCode('Tried to use \'add\' after querying the source set')
        when = listify(kwargs.get('when', []))
        if_true = listify(kwargs.get('if_true', []))
        if_false = listify(kwargs.get('if_false', []))
        if not when and not if_true and not if_false:
            if_true = args
        elif args:
            raise InterpreterException('add called with both positional and keyword arguments')
        keys, dependencies = self.check_conditions(when)
        sources, extra_deps = self.check_source_files(if_true, True)
        if_false, _ = self.check_source_files(if_false, False)
        self.held_object.append(SourceSetRule(keys, sources, if_false, [], dependencies, extra_deps))

    @permittedKwargs(['when', 'if_true'])
    def add_all_method(self, args, kwargs):
        if self.frozen:
            raise InvalidCode('Tried to use \'add_all\' after querying the source set')
        when = listify(kwargs.get('when', []))
        if_true = listify(kwargs.get('if_true', []))
        if not when and not if_true:
            if_true = args
        elif args:
            raise InterpreterException('add_all called with both positional and keyword arguments')
        keys, dependencies = self.check_conditions(when)
        for s in if_true:
            if not isinstance(s, SourceSetHolder):
                raise InvalidCode('Arguments to \'add_all\' after the first must be source sets')
            s.frozen = True
        self.held_object.append(SourceSetRule(keys, [], [], if_true, dependencies, []))

    def collect(self, enabled_fn, all_sources, into=None):
        if not into:
            into = SourceFiles(set(), set())
        for entry in self.held_object:
            if all(x.found() for x in entry.dependencies) and \
               all(enabled_fn(key) for key in entry.keys):
                into.sources.update(entry.sources)
                into.dependencies.update(entry.dependencies)
                into.dependencies.update(entry.extra_deps)
                for ss in entry.sourcesets:
                    ss.collect(enabled_fn, all_sources, into)
                if not all_sources:
                    continue
            into.sources.update(entry.if_false)
        return into

    @noKwargs
    @noPosargs
    def all_sources_method(self, args, kwargs):
        self.frozen = True
        files = self.collect(lambda x: True, True)
        return list(files.sources)

    @noKwargs
    @noPosargs
    @FeatureNew('source_set.all_dependencies() method', '0.52.0')
    def all_dependencies_method(self, args, kwargs):
        self.frozen = True
        files = self.collect(lambda x: True, True)
        return list(files.dependencies)

    @permittedKwargs(['strict'])
    def apply_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Apply takes exactly one argument')
        config_data = args[0]
        self.frozen = True
        strict = kwargs.get('strict', True)
        if isinstance(config_data, dict):
            def _get_from_config_data(key):
                if strict and key not in config_data:
                    raise InterpreterException('Entry {} not in configuration dictionary.'.format(key))
                return config_data.get(key, False)
        else:
            config_cache = dict()

            def _get_from_config_data(key):
                nonlocal config_cache
                if key not in config_cache:
                    args = [key] if strict else [key, False]
                    config_cache[key] = config_data.get_method(args, {})
                return config_cache[key]

        files = self.collect(_get_from_config_data, False)
        res = SourceFilesHolder(files)
        return res

class SourceFilesHolder(InterpreterObject, ObjectHolder):
    def __init__(self, files):
        InterpreterObject.__init__(self)
        ObjectHolder.__init__(self, files)
        self.methods.update({
            'sources': self.sources_method,
            'dependencies': self.dependencies_method,
        })

    @noPosargs
    @noKwargs
    def sources_method(self, args, kwargs):
        return list(self.held_object.sources)

    @noPosargs
    @noKwargs
    def dependencies_method(self, args, kwargs):
        return list(self.held_object.dependencies)

class SourceSetModule(ExtensionModule):
    @FeatureNew('SourceSet module', '0.51.0')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.snippets.add('source_set')

    @noKwargs
    @noPosargs
    def source_set(self, interpreter, state, args, kwargs):
        return SourceSetHolder(interpreter)

def initialize(*args, **kwargs):
    return SourceSetModule(*args, **kwargs)
