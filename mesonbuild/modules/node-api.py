# SPDX-License-Identifier: Apache-2.0
# Copyright 2024 momtchil@momtchev.com
# Inspired by the python.py module

from __future__ import annotations

import json, subprocess, os, sys, tarfile, io
import urllib.request, urllib.error, urllib.parse
from pathlib import Path
import typing as T

from . import ExtensionModule, ModuleInfo
from .. import mesonlib
from .. import mlog
from ..build import known_shmod_kwargs, CustomTarget, CustomTargetIndex, BuildTarget, GeneratedList, StructuredSources, ExtractedObjects, SharedModule
from ..programs import ExternalProgram
from ..interpreter.type_checking import SHARED_MOD_KWS, TEST_KWS
from ..interpreterbase import (
    permittedKwargs, typed_pos_args, typed_kwargs, KwargInfo
)

if T.TYPE_CHECKING:
    from . import ModuleState
    from ..interpreter import Interpreter
    from ..interpreter.kwargs import SharedModule as SharedModuleKw, FuncTest as FuncTestKw
    from .. import options
    from typing import Any
    from typing_extensions import TypedDict

    SourcesVarargsType = T.List[T.Union[str, mesonlib.File, CustomTarget, CustomTargetIndex, GeneratedList, StructuredSources, ExtractedObjects, BuildTarget]]

    class NodeAPIOptions(TypedDict):
        async_pool:     int
        es6:            bool
        stack:          str
        swig:           bool
        environments:   T.List[str]

name_prefix = ''
name_suffix_native = 'node'
name_suffix_wasm_es6 = 'mjs'
name_suffix_wasm_cjs = 'js'

mod_kwargs = {'node_api_options'}
mod_kwargs.update(known_shmod_kwargs)
mod_kwargs -= {'name_prefix', 'name_suffix'}

_MOD_KWARGS = [k for k in SHARED_MOD_KWS if k.name not in {'name_prefix', 'name_suffix'}]

# These are the defauls
node_api_defaults: 'NodeAPIOptions' = {
    'async_pool':       4,
    'es6':              True,
    'stack':            '2MB',
    'swig':             False,
    'environments':     ['node', 'web', 'webview', 'worker']
}
_NODE_API_OPTS_KW = KwargInfo('node_api_options', dict, default=node_api_defaults)

swig_cpp_defaults_shared = [
    '-Wno-deprecated-declarations',
    '-Wno-unused-function',
    '-Wno-type-limits',
    '-Wno-deprecated-copy',
    '-Wno-attributes'
]
swig_cpp_defaults_clang = swig_cpp_defaults_shared + [
    '-Wno-deprecated-declarations',
    '-Wno-unused-function',
    '-Wno-type-limits',
    '-Wno-deprecated-copy',
    '-Wno-attributes',
    '-Wno-sometimes-uninitialized'
]
swig_cpp_defaults = {
    'gcc': swig_cpp_defaults_shared + ['-Wno-maybe-uninitialized'],
    'clang': swig_cpp_defaults_clang,
    'msvc': ['/wo6246', '/wo28182'],
    'emscripten': swig_cpp_defaults_clang
}
# These are options that have special (and incompatible) meaning in both npm and meson
# Keep them apart
npm_config_blacklist = [
    'prefix'
]

if T.TYPE_CHECKING:
    class ExtensionModuleKw(SharedModuleKw):
        node_api_options: 'NodeAPIOptions'
        # These are missing from the base type
        install_dir: str
        link_args: T.List[str]

def tar_strip1(files: T.List[tarfile.TarInfo]) -> T.Generator[tarfile.TarInfo, None, None]:
    for member in files:
        member.path = str(Path(*Path(member.path).parts[1:]))
        yield member

class NapiModule(ExtensionModule):

    INFO = ModuleInfo('node-api', '1.5.0')

    def __init__(self, interpreter: 'Interpreter') -> None:
        super().__init__(interpreter)
        self.node_process: Any = None
        self.node_addon_api_package: Any = None
        self.emnapi_package: Any = None
        self.napi_dir: Path = None
        self.napi_includes: Path = None
        self.napi_lib: Path = None
        self.source_root: Path = Path(interpreter.environment.get_source_dir())
        self.load_node_process()
        self.download_headers()
        self.methods.update({
            'extension_module': self.extension_module_method,
            'test': self.test_method,
        })
        self.parse_npm_options()

    def parse_node_json_output(self, code: str) -> Any:
        result: Any = None
        try:
            node_json = subprocess.Popen(['node', '-p', f'JSON.stringify({code})'], shell=False,
                                         stdout=subprocess.PIPE, cwd=self.source_root)
            data, err = node_json.communicate()
            node_json.wait()
            result = json.loads(data)
        except Exception as e:
            raise mesonlib.MesonException(f'Failed spawning node: {str(e)}')
        return result

    def load_node_process(self) -> None:
        if self.node_process is None:
            self.node_process = self.parse_node_json_output('process')
            self.get_napi_dir()

    def load_node_addon_api_package(self) -> None:
        if self.node_addon_api_package is None:
            self.node_addon_api_package = self.parse_node_json_output('require("node-addon-api")')

    def load_emnapi_package(self) -> None:
        if self.emnapi_package is None:
            self.emnapi_package = self.parse_node_json_output('require("emnapi")')

    def construct_swig_options(self, opts: 'NodeAPIOptions') -> T.List[str]:
        if opts['swig']:
            cpp_id = self.interpreter.environment.coredata.compilers.host['cpp'].id
            if cpp_id in swig_cpp_defaults:
                return swig_cpp_defaults[cpp_id]
        return []

    def construct_native_options(self, name: str, opts: 'NodeAPIOptions') -> T.Tuple[T.List[str], T.List[str], T.List[str]]:
        return [], self.construct_swig_options(opts), []

    # As these options are mandatory in order to build an emnapi WASM module, they are hardcoded here
    def construct_emscripten_options(self, name: str, opts: 'NodeAPIOptions') -> T.Tuple[T.List[str], T.List[str], T.List[str]]:
        c_args = []
        cpp_args = self.construct_swig_options(opts)
        link_args = ['-Wno-emcc', '-Wno-pthreads-mem-growth', '-sALLOW_MEMORY_GROWTH=1',
                     '-sEXPORTED_FUNCTIONS=["_malloc","_free","_napi_register_wasm_v1","_node_api_module_get_api_version_v1"]',
                     '--bind', f'-sSTACK_SIZE={opts["stack"]}']

        if opts['es6']:
            link_args.extend(['-sMODULARIZE', '-sEXPORT_ES6=1', f'-sEXPORT_NAME={name}'])
        # emscripten cannot link code compiled with -pthread with code compiled without it
        c_thread_count: int = self.interpreter.environment.coredata.options[mesonlib.OptionKey('thread_count', lang='c')].value
        cpp_thread_count: int = 0
        if 'cpp' in self.interpreter.environment.coredata.compilers.host:
            cpp_thread_count = self.interpreter.environment.coredata.options[mesonlib.OptionKey('thread_count', lang='cpp')].value
            exceptions = self.interpreter.environment.coredata.options[mesonlib.OptionKey('eh', lang='cpp')].value != 'none'
            if exceptions:
                cpp_args.append('-sNO_DISABLE_EXCEPTION_CATCHING')
                link_args.append('-sNO_DISABLE_EXCEPTION_CATCHING')
            if not exceptions and opts['swig']:
                raise mesonlib.MesonException('SWIG-JSE requires C++ exceptions')

        if c_thread_count or cpp_thread_count:
            c_args.append(f'-DEMNAPI_WORKER_POOL_SIZE={opts["async_pool"]}')
            cpp_args.append(f'-DEMNAPI_WORKER_POOL_SIZE={opts["async_pool"]}')
            link_args.append(f'-sDEFAULT_PTHREAD_STACK_SIZE={opts["stack"]}')

        env = '-sENVIRONMENT='
        for e in opts['environments']:
            if e in node_api_defaults['environments']:
                env += f'{e},'
            else:
                mlog.warning(f'Ignoring invalid environments {e}')
        link_args.append(env)

        return c_args, cpp_args, link_args

    def get_napi_dir(self) -> None:
        if sys.platform in 'linux':
            home = os.environ['HOME'] if 'HOME' in os.environ else '/tmp'
            self.napi_dir = Path(home) / '.cache' / 'node-hadron' / self.node_process['release']['name'] / self.node_process['version']
        elif sys.platform == 'darwin':
            home = os.environ['HOME'] if 'HOME' in os.environ else '/tmp'
            self.napi_dir = Path(home) / 'Library' / 'Caches' / 'node-hadron' / self.node_process['release']['name'] / self.node_process['version']
        elif sys.platform == 'win32':
            home = os.environ['LOCALAPPDATA'] if 'LOCALAPPDATA' in os.environ else 'C:\\'
            self.napi_dir = Path(home) / 'node-hadron' / self.node_process['release']['name'] / self.node_process['version']
        else:
            raise mesonlib.MesonException(f'Unsupported platform: {sys.platform}')

    def download_item(self, url: str, dest: Path) -> None:
        try:
            remote = urllib.request.urlopen(url)
            if url.endswith('.tar.gz'):
                if not os.path.exists(dest):
                    mlog.log(f'Downloading {url} to {dest}')
                    with tarfile.open(fileobj=io.BytesIO(remote.read()), mode='r:gz') as input:
                        input.extractall(path=dest, members=tar_strip1(input.getmembers()))
            else:
                filename = urllib.parse.urlparse(url)
                file = Path(dest, os.path.basename(filename.path))
                if not os.path.exists(file):
                    mlog.log(f'Downloading {url} to {str(file)}')
                    with file.open('wb') as output:
                        output.write(remote.read())
        except Exception as e:
            raise mesonlib.MesonException(f'Failed downloading from {url}: {str(e)}')

    def download_headers(self) -> None:
        if 'headersUrl' in self.node_process['release']:
            self.download_item(self.node_process['release']['headersUrl'], self.napi_dir)
            self.napi_includes = self.napi_dir / 'include' / 'node'
        if 'libUrl' in self.node_process['release']:
            url = self.node_process['release']['libUrl']
            self.download_item(url, self.napi_dir)
            self.napi_lib = self.napi_dir / os.path.basename(urllib.parse.urlparse(url).path)

        mlog.log('Node.js library distribution: ', mlog.bold(str(self.napi_dir)))

    # Transform path to relative if it is inside the project subdir
    # Use ../.. if it is relative to the project root, but not the project subdir
    def relativize(self, p: T.Union[str, Path], source_dir: Path) -> Path:
        r: Path = p if isinstance(p, Path) else Path(p)
        if mesonlib.path_is_in_root(r, source_dir, resolve=True):
            return r.relative_to(source_dir)
        if not mesonlib.path_is_in_root(r, self.source_root, resolve=True):
            return r
        # This requires walk_up in pathlib which requires Python 3.12
        # In node-api, compiling a 'subdir' requires including ../node_modules/node-addon-api
        return Path(os.path.relpath(str(r), str(source_dir)))

    # Transform path to absolute relative to the project root (package.json)
    def resolve(self, p: T.Union[str, Path]) -> Path:
        r: Path = p if isinstance(p, Path) else Path(p)
        if r.is_absolute():
            return r
        return self.source_root / r

    def emnapi_sources(self, source_root: Path) -> T.List[Path]:
        self.load_emnapi_package()
        sources: T.List[str] = self.emnapi_package['sources']
        return [self.relativize(self.resolve(d), source_root) for d in sources]

    def emnapi_include_dirs(self, source_root: Path) -> T.List[Path]:
        self.load_emnapi_package()
        inc_dirs: T.List[str] = [self.emnapi_package['include_dir']]
        return [self.relativize(self.resolve(d), source_root) for d in inc_dirs]

    def emnapi_js_library(self, source_root: Path) -> Path:
        self.load_emnapi_package()
        js_lib: str = self.emnapi_package['js_library']
        return Path(js_lib)

    def parse_npm_options(self) -> None:
        for key in self.interpreter.environment.coredata.options.keys():
            if key.name in npm_config_blacklist:
                continue
            opt = self.interpreter.environment.coredata.options[key]
            env_name = key.name if key.lang is None else f'{key.lang}_{key.name}'
            if isinstance(opt.value, str):
                if 'npm_config_' + env_name in os.environ:
                    opt.set_value(os.environ['npm_config_' + env_name])
            if isinstance(opt.value, bool):
                npm_enable = 'npm_config_enable_' + env_name in os.environ
                npm_disable = 'npm_config_disable_' + env_name in os.environ
                if npm_enable and npm_disable:
                    l = list(os.environ.keys())
                    mlog.warning(f'Found both --enable-{env_name} and --disable-{env_name}, last one wins')
                    opt.set_value(l.index('npm_config_enable_' + env_name) > l.index('npm_config_disable_' + env_name))
                elif npm_enable:
                    opt.set_value(True)
                elif npm_disable:
                    opt.set_value(False)
            if isinstance(opt.value, list):
                if 'npm_config_' + env_name in os.environ:
                    T.cast('options.UserArrayOption', opt).extend_value(os.environ['npm_config_' + env_name])

    @permittedKwargs(mod_kwargs)
    @typed_pos_args('node-api.extension_module', str, varargs=(str, mesonlib.File, CustomTarget, CustomTargetIndex, GeneratedList, StructuredSources, ExtractedObjects, BuildTarget))
    # TODO: For some strange reason, install_dir requires allow_unknown=True
    @typed_kwargs('node-api.extension_module', *_MOD_KWARGS, _NODE_API_OPTS_KW, allow_unknown=True)
    def extension_module_method(self, state: 'ModuleState', args: T.Tuple[str, SourcesVarargsType], kwargs: ExtensionModuleKw) -> 'SharedModule':
        if 'include_directories' not in kwargs:
            kwargs['include_directories'] = []
        kwargs['name_prefix'] = name_prefix
        source_dir = self.source_root / state.subdir
        kwargs.setdefault('install_dir', '')

        cons_args = None
        opts = T.cast('NodeAPIOptions', {**node_api_defaults, **kwargs['node_api_options']})
        if self.interpreter.environment.machines.host.system == 'emscripten':
            # emscripten WASM mode
            if 'c' not in self.interpreter.environment.get_coredata().compilers.host:
                raise mesonlib.MesonException('Node-API requires C to be enabled for WASM mode')

            kwargs['name_suffix'] = name_suffix_wasm_es6 if opts['es6'] else name_suffix_wasm_cjs
            cons_args = self.construct_emscripten_options

            js_lib = self.emnapi_js_library(source_dir)
            kwargs.setdefault('link_args', []).append(f'--js-library={js_lib}')

            inc_dirs = self.emnapi_include_dirs(source_dir)
            kwargs['include_directories'] += [str(d) for d in inc_dirs]

            sources = self.emnapi_sources(source_dir)
            args[1].extend([str(d) for d in sources])

        else:
            # Node.js native mode
            kwargs['name_suffix'] = name_suffix_native
            cons_args = self.construct_native_options

            if self.napi_lib:
                napi_lib = self.relativize(self.napi_lib, source_dir)
                kwargs.setdefault('objects', []).extend([str(napi_lib)])

        extra_c_args, extra_cpp_args, extra_link_args = cons_args(args[0], opts)
        kwargs.setdefault('link_args', []).extend(extra_link_args)
        kwargs.setdefault('c_args', []).extend(extra_c_args)
        kwargs.setdefault('cpp_args', []).extend(extra_cpp_args)

        if 'cpp' in self.interpreter.environment.coredata.compilers.host:
            self.load_node_addon_api_package()
            inc_dir = self.node_addon_api_package['include'].strip('\"')
            node_addon_api_dir = self.relativize(inc_dir, source_dir)
            kwargs.setdefault('include_directories', []).extend([str(node_addon_api_dir)])
            kwargs.setdefault('override_options', {})
            # The default C++ standard when using node-addon-api should be C++17
            cpp_std_key = mesonlib.OptionKey('std', lang='cpp')
            if cpp_std_key not in kwargs['override_options']:
                kwargs['override_options'][cpp_std_key] = 'c++17'

        if self.napi_includes:
            napi_includes = self.relativize(self.napi_includes, source_dir)
            kwargs.setdefault('include_directories', []).extend([str(napi_includes)])

        return self.interpreter.build_target(state.current_node, args, kwargs, SharedModule)

    @typed_pos_args('node_api.test', str, (str, mesonlib.File), (SharedModule, mesonlib.File))
    @typed_kwargs('node_api.test', *TEST_KWS, KwargInfo('is_parallel', bool, default=True))
    def test_method(self, state: 'ModuleState',
                    args: T.Tuple[
                        str,
                        T.Union[str, mesonlib.File],
                        T.Union[SharedModule, mesonlib.File]
                        ],
                    kwargs: 'FuncTestKw') -> None:

        test_name = args[0]
        script = args[1]
        addon = args[2]

        node_script: mesonlib.File = None
        if isinstance(script, mesonlib.File):
            node_script = script
        else:
            node_script = mesonlib.File(False, state.subdir, script)

        node_env = kwargs.setdefault('env', mesonlib.EnvironmentVariables())
        node_addon: T.Union[SharedModule, mesonlib.File] = None
        node_path: str = None
        if isinstance(addon, SharedModule):
            kwargs.setdefault('depends', []).append(addon)
            node_path = str((Path(self.interpreter.environment.get_build_dir()) / addon.subdir).resolve())
            node_addon = addon
            node_env.set('NODE_ADDON', [node_addon.filename])
        elif isinstance(addon, mesonlib.File):
            node_path = addon.absolute_path()
            node_addon = addon
            node_env.set('NODE_ADDON', [str(node_addon.relative_name)])
        else:
            raise mesonlib.MesonException('The target must be either a napi.ExtensionModule or an ExternalProgram')
        node_env.set('NODE_PATH', [node_path])

        kwargs.setdefault('args', []).insert(0, node_script)

        self.interpreter.add_test(state.current_node, (test_name, ExternalProgram('node')), T.cast('T.Dict[str, Any]', kwargs), True)

def initialize(interpreter: 'Interpreter') -> NapiModule:
    mod = NapiModule(interpreter)
    return mod
