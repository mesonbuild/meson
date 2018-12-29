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


from . import coredata as cdata

import os.path
import pprint
import textwrap

def add_arguments(parser):
    parser.add_argument('--all', action='store_true', dest='all', default=False,
                        help='Show data not used by current backend.')

    parser.add_argument('builddir', nargs='?', default='.', help='The build directory')


def dump_compilers(compilers):
    for lang, compiler in compilers.items():
        print('  ' + lang + ':')
        print('      Id: ' + compiler.id)
        print('      Command: ' + ' '.join(compiler.exelist))
        print('      Full version: ' + compiler.full_version)
        print('      Detected version: ' + compiler.version)
        print('      Detected type: ' + repr(compiler.compiler_type))
        #pprint.pprint(compiler.__dict__)


def dump_guids(d):
    for name, value in d.items():
        print('  ' + name + ': ' + value)


def run(options):
    datadir = 'meson-private'
    if options.builddir is not None:
        datadir = os.path.join(options.builddir, datadir)
    if not os.path.isdir(datadir):
        print('Current directory is not a build dir. Please specify it or '
              'change the working directory to it.')
        return 1

    all = options.all

    print('This is a dump of the internal unstable cache of meson. This is for debugging only.')
    print('Do NOT parse, this will change from version to version in incompatible ways')
    print('')

    coredata = cdata.load(options.builddir)
    backend = coredata.get_builtin_option('backend')
    for k, v in sorted(coredata.__dict__.items()):
        if k in ('backend_options', 'base_options', 'builtins', 'compiler_options', 'user_options'):
            # use `meson configure` to view these
            pass
        elif k in ['install_guid', 'test_guid', 'regen_guid']:
            if all or backend.startswith('vs'):
                print(k + ': ' + v)
        elif k == 'target_guids':
            if all or backend.startswith('vs'):
                print(k + ':')
                dump_guids(v)
        elif k in ['lang_guids']:
            if all or backend.startswith('vs') or backend == 'xcode':
                print(k + ':')
                dump_guids(v)
        elif k == 'meson_command':
            if all or backend.startswith('vs'):
                print('Meson command used in build file regeneration: ' + ' '.join(v))
        elif k == 'pkgconf_envvar':
            print('Last seen PKGCONFIG enviroment variable value: ' + v)
        elif k == 'version':
            print('Meson version: ' + v)
        elif k == 'cross_file':
            print('Cross File: ' + (v or 'None'))
        elif k == 'config_files':
            if v:
                print('Native File: ' + ' '.join(v))
        elif k == 'compilers':
            print('Cached native compilers:')
            dump_compilers(v)
        elif k == 'cross_compilers':
            print('Cached cross compilers:')
            dump_compilers(v)
        elif k == 'deps':
            native = []
            cross = []
            for dep_key, dep in sorted(v.items()):
                if dep_key[2]:
                    cross.append((dep_key, dep))
                else:
                    native.append((dep_key, dep))

            def print_dep(dep_key, dep):
                print('  ' + dep_key[0] + ": ")
                print('      compile args: ' + repr(dep.get_compile_args()))
                print('      link args: ' + repr(dep.get_link_args()))
                if dep.get_sources():
                    print('      sources: ' + repr(dep.get_sources()))
                print('      version: ' + repr(dep.get_version()))

            if native:
                print('Cached native dependencies:')
                for dep_key, dep in native:
                    print_dep(dep_key, dep)
            if cross:
                print('Cached dependencies:')
                for dep_key, dep in cross:
                    print_dep(dep_key, dep)
        elif k == 'external_preprocess_args':
            for lang, opts in v.items():
                if opts:
                    print('Preprocessor args for ' + lang + ': ' + ' '.join(opts))
        else:
            print(k + ':')
            print(textwrap.indent(pprint.pformat(v), '  '))
