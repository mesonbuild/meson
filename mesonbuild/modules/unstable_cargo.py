# Copyright 2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json

from .. import mlog
from ..mesonlib import Popen_safe, Popen_safe_errors
from ..mesonlib import extract_as_list, version_compare, MesonException, File
from ..environment import for_windows, for_cygwin, for_darwin
from ..interpreterbase import noKwargs, permittedKwargs
from ..dependencies import InternalDependency
from ..build import CustomTarget

from . import ExtensionModule, ModuleReturnValue, permittedSnippetKwargs

target_kwargs = {'toml', 'sources', 'install', 'install_dir'}


class CargoModule(ExtensionModule):
    cargo = ['cargo']
    cargo_build = ['cargo', 'build', '-v', '--color=always']
    cargo_version = None

    def __init__(self):
        super().__init__()
        try:
            self._get_version()
        except Popen_safe_errors:
            raise MesonException('Cargo was not found')
        self.snippets.add('test')
        self.snippets.add('benchmark')

    def _get_cargo_build(self, toml):
        # FIXME: must use target-triple to set the host system, currently it
        # always builds for the build machine.
        return self.cargo_build + ['--manifest-path', toml]

    def _is_release(self, env):
        buildtype = env.coredata.get_builtin_option('buildtype')
        return not buildtype.startswith('debug')

    def _get_crate_name(self, name, crate_type, env):
        '''
        We have no control over what filenames cargo uses for its output, so we
        have to figure it out ourselves.
        '''
        if for_cygwin(env.is_cross_build(), env):
            raise MesonException('Cygwin cargo support is TODO')
        prefix = 'lib'
        if crate_type == 'staticlib':
            suffix = 'a'
            if for_windows(env.is_cross_build(), env):
                prefix = ''
                suffix = 'lib'
        elif crate_type == 'cdylib':
            if for_windows(env.is_cross_build(), env):
                prefix = ''
                suffix = 'dll'
            elif for_darwin(env.is_cross_build(), env):
                suffix = 'dylib'
            else:
                suffix = 'so'
        elif crate_type == 'bin':
            prefix = ''
            suffix = ''
            if for_windows(env.is_cross_build(), env):
                suffix = 'exe'
        if suffix:
            fname = prefix + name + '.' + suffix
        else:
            fname = prefix + name
        if self._is_release(env):
            return os.path.join('release', fname)
        else:
            return os.path.join('debug', fname)

    def _read_metadata(self, toml):
        cmd = self.cargo + ['metadata', '--format-version=1', '--no-deps',
                            '--manifest-path', toml]
        out = Popen_safe(cmd)[1]
        try:
            encoded = json.loads(out)
        except json.decoder.JSONDecodeError:
            print(cmd, out)
            raise
        return encoded['packages'][0]

    def _source_strings_to_files(self, source_dir, subdir, sources):
        results = []
        for s in sources:
            if isinstance(s, File):
                pass
            elif isinstance(s, str):
                s = File.from_source_file(source_dir, subdir, s)
            else:
                raise MesonException('Source item is {!r} instead of '
                                     'string or files() object'.format(s))
            results.append(s)
        return results

    def _get_sources(self, state, kwargs):
        # 'sources' kwargs is optional; we have a depfile with dependency
        # information and ninja will use that to determine when to rebuild.
        sources = extract_as_list(kwargs, 'sources')
        return self._source_strings_to_files(state.environment.source_dir,
                                             state.subdir, sources)

    def _get_cargo_test_outputs(self, name, metadata, env):
        args = []
        outputs = []
        depfile = None
        for t in metadata['targets']:
            if t['name'] != name:
                continue
            # Filter out crate types we don't want
            # a test target will only have one output
            if t['crate_types'] != ['bin']:
                continue
            # Filter out the target `kind`s that we don't want
            if t['kind'] != ['test']:
                continue
            outputs.append(self._get_crate_name(name, 'bin', env))
            args = ['--test', name]
            break
        if outputs:
            depfile = os.path.splitext(outputs[0])[0] + '.d'
        else:
            toml = metadata['manifest_path']
            raise MesonException('no test called {!r} found in {!r}'
                                 ''.format(name, toml))
        return outputs, depfile, args

    def _get_cargo_executable_outputs(self, name, metadata, env):
        args = []
        outputs = []
        depfile = None
        for t in metadata['targets']:
            if t['name'] != name:
                continue
            # Filter out crate types we don't want
            # an executable target will only have one output
            if t['crate_types'] != ['bin']:
                continue
            # Filter out the target `kind`s that we don't want
            if t['kind'] not in [['example'], ['bin']]:
                continue
            outputs.append(self._get_crate_name(name, 'bin', env))
            if t['kind'][0] == 'example':
                args = ['--example', name]
            else:
                args = ['--bin', name]
            break
        if outputs:
            depfile = os.path.splitext(outputs[0])[0] + '.d'
        else:
            toml = metadata['manifest_path']
            raise MesonException('no bin called {!r} found in {!r}'
                                 ''.format(name, toml))
        return outputs, depfile, args

    def _get_cargo_static_library_outputs(self, name, metadata, env):
        args = []
        outputs = []
        depfile = None
        for t in metadata['targets']:
            if t['name'] != name:
                continue
            # Filter out the target `kind`s that we don't want
            # a library target can have multiple outputs
            if 'staticlib' not in t['kind'] and \
               'example' not in t['kind']:
                continue
            for ct in t['crate_types']:
                if ct == 'staticlib':
                    outputs.append(self._get_crate_name(name, ct, env))
            if t['kind'][0] == 'example':
                # If the library is an example, it must be built by name
                args = ['--example', name]
            else:
                # Library is the crate itself, no name needed
                args = ['--lib']
            break
        if outputs:
            depfile = os.path.splitext(outputs[0])[0] + '.d'
        else:
            toml = metadata['manifest_path']
            raise MesonException('no staticlib called {!r} found '
                                 'in {!r}'.format(name, toml))
        return outputs, depfile, args

    def _get_cargo_outputs(self, name, metadata, env, cargo_target_type):
        # FIXME: track which outputs have already been fetched from
        # a toml file and disallow duplicates.
        fn = getattr(self, '_get_cargo_{}_outputs'.format(cargo_target_type))
        return fn(name, metadata, env)

    def _check_cargo_dep_info_bug(self, metadata):
        if version_compare(self.cargo_version, '>0.22.0'):
            return
        for t in metadata['targets']:
            if t['kind'] == ['custom-build']:
                m = 'Crate {!r} contains a custom build script {!r} which ' \
                    'will cause dep-info to not being emitted due to a ' \
                    'bug in Cargo. Please upgrade to Cargo 0.23 or newer.' \
                    ''.format(metadata['name'], os.path.basename(t['src_path']))
                mlog.warning(m)
                return

    def _cargo_target(self, state, args, kwargs, cargo_target_type):
        ctkwargs = {}
        env = state.environment
        if len(args) != 1:
            raise MesonException('{0}() requires exactly one positional '
                                 'argument: the name of the {0}'
                                 ''.format(cargo_target_type))
        name = args[0]
        if 'toml' not in kwargs:
            raise MesonException('"toml" kwarg is required')
        toml = File.from_source_file(env.get_source_dir(), state.subdir,
                                     kwargs['toml'])
        # Get the Cargo.toml file as a JSON encoded object
        md = self._read_metadata(toml.absolute_path(env.source_dir, None))
        # Warn about the cargo dep-info bug if needed
        self._check_cargo_dep_info_bug(md)
        # Get the list of outputs that cargo will create matching the specified name
        ctkwargs['output'], ctkwargs['depfile'], cargo_args = \
            self._get_cargo_outputs(name, md, env, cargo_target_type)
        # Set the files that will trigger a rebuild
        ctkwargs['depend_files'] = [toml] + self._get_sources(state, kwargs)
        # Cargo command that will build the output library/libraries/bins
        cmd = self._get_cargo_build(toml) + cargo_args
        if self._is_release(env):
            cmd.append('--release')
        ctkwargs['command'] = cmd
        if 'install' in kwargs:
            ctkwargs['install'] = kwargs['install']
        if 'install_dir' in kwargs:
            ctkwargs['install_dir'] = kwargs['install_dir']
        elif 'install' in kwargs:
            # People should be able to set `install: true` and get a good
            # default for `install_dir`
            if cargo_target_type == 'static_library':
                ctkwargs['install_dir'] = env.coredata.get_builtin_option('libdir')
            elif cargo_target_type == 'executable':
                ctkwargs['install_dir'] = env.coredata.get_builtin_option('bindir')
        ct = CustomTarget(name, state.subdir, state.subproject, ctkwargs)
        # Ninja buffers all cargo output so we get no status updates
        ct.ninja_pool = 'console'
        # Force it to output in the current directory
        ct.envvars['CARGO_TARGET_DIR'] = state.subdir
        # XXX: we need to call `cargo clean` on `ninja clean`.
        return md, ct

    @permittedKwargs(target_kwargs)
    def static_library(self, state, args, kwargs):
        md, ct = self._cargo_target(state, args, kwargs, 'static_library')
        # XXX: Cargo build outputs a list of system libraries that are needed
        # by this (possibly) static library, but we have no way of accessing it
        # during configure. So we require developers to manage that themselves.
        # XXX: We add the output file into `sources`, but that creates
        # a compile-time dependency instead of a link-time dependency and
        # reduces parallelism.
        d = InternalDependency(md['version'], [], [], [], [], [ct], [])
        return ModuleReturnValue(d, [d])

    @permittedKwargs(target_kwargs)
    def executable(self, state, args, kwargs):
        md, ct = self._cargo_target(state, args, kwargs, 'executable')
        # XXX: We return a custom target, which means this may not be usable
        # everywhere that an executable build target can be.
        return ModuleReturnValue(ct, [ct])

    @permittedSnippetKwargs(target_kwargs)
    def test(self, interpreter, state, args, kwargs):
        # This would map to cargo tests
        raise MesonException('Not implemented')

    @permittedSnippetKwargs(target_kwargs)
    def benchmark(self, interpreter, state, args, kwargs):
        # This would map to cargo benches
        raise MesonException('Not implemented')

    def _get_version(self):
        if self.cargo_version is None:
            out = Popen_safe(self.cargo + ['--version'])[1]
            self.cargo_version = out.strip().split('cargo ')[1]
        return self.cargo_version

    @noKwargs
    def version(self, state, args, kwargs):
        return ModuleReturnValue(self._get_version(), [])


def initialize():
    return CargoModule()
