import functools

from ..interpreterbase.decorators import typed_kwargs, KwargInfo

from .interpreterobjects import (extract_required_kwarg, extract_search_dirs)

from .. import mesonlib
from .. import mlog
from .. import dependencies
from ..interpreterbase import (ObjectHolder, noPosargs, noKwargs, permittedKwargs,
                               FeatureNew, FeatureNewKwargs, disablerIfNotFound,
                               check_stringlist, InterpreterException, InvalidArguments)

import typing as T
import os

if T.TYPE_CHECKING:
    from ..interpreter import Interpreter
    from ..compilers import Compiler, RunResult

class TryRunResultHolder(ObjectHolder['RunResult']):
    def __init__(self, res: 'RunResult', interpreter: 'Interpreter'):
        super().__init__(res, interpreter)
        self.methods.update({'returncode': self.returncode_method,
                             'compiled': self.compiled_method,
                             'stdout': self.stdout_method,
                             'stderr': self.stderr_method,
                             })

    @noPosargs
    @permittedKwargs({})
    def returncode_method(self, args, kwargs):
        return self.held_object.returncode

    @noPosargs
    @permittedKwargs({})
    def compiled_method(self, args, kwargs):
        return self.held_object.compiled

    @noPosargs
    @permittedKwargs({})
    def stdout_method(self, args, kwargs):
        return self.held_object.stdout

    @noPosargs
    @permittedKwargs({})
    def stderr_method(self, args, kwargs):
        return self.held_object.stderr

header_permitted_kwargs = {
    'required',
    'prefix',
    'no_builtin_args',
    'include_directories',
    'args',
    'dependencies',
}

find_library_permitted_kwargs = {
    'has_headers',
    'required',
    'dirs',
    'static',
}

find_library_permitted_kwargs |= {'header_' + k for k in header_permitted_kwargs}

class CompilerHolder(ObjectHolder['Compiler']):
    def __init__(self, compiler: 'Compiler', interpreter: 'Interpreter'):
        super().__init__(compiler, interpreter)
        self.environment = self.env
        self.methods.update({'compiles': self.compiles_method,
                             'links': self.links_method,
                             'get_id': self.get_id_method,
                             'get_linker_id': self.get_linker_id_method,
                             'compute_int': self.compute_int_method,
                             'sizeof': self.sizeof_method,
                             'get_define': self.get_define_method,
                             'check_header': self.check_header_method,
                             'has_header': self.has_header_method,
                             'has_header_symbol': self.has_header_symbol_method,
                             'run': self.run_method,
                             'has_function': self.has_function_method,
                             'has_member': self.has_member_method,
                             'has_members': self.has_members_method,
                             'has_type': self.has_type_method,
                             'alignment': self.alignment_method,
                             'version': self.version_method,
                             'cmd_array': self.cmd_array_method,
                             'find_library': self.find_library_method,
                             'has_argument': self.has_argument_method,
                             'has_function_attribute': self.has_func_attribute_method,
                             'get_supported_function_attributes': self.get_supported_function_attributes_method,
                             'has_multi_arguments': self.has_multi_arguments_method,
                             'get_supported_arguments': self.get_supported_arguments_method,
                             'first_supported_argument': self.first_supported_argument_method,
                             'has_link_argument': self.has_link_argument_method,
                             'has_multi_link_arguments': self.has_multi_link_arguments_method,
                             'get_supported_link_arguments': self.get_supported_link_arguments_method,
                             'first_supported_link_argument': self.first_supported_link_argument_method,
                             'unittest_args': self.unittest_args_method,
                             'symbols_have_underscore_prefix': self.symbols_have_underscore_prefix_method,
                             'get_argument_syntax': self.get_argument_syntax_method,
                             })

    @property
    def compiler(self) -> 'Compiler':
        return self.held_object

    def _dep_msg(self, deps, endl):
        msg_single = 'with dependency {}'
        msg_many = 'with dependencies {}'
        if not deps:
            return endl
        if endl is None:
            endl = ''
        names = []
        for d in deps:
            if isinstance(d, dependencies.InternalDependency):
                continue
            if isinstance(d, dependencies.ExternalLibrary):
                name = '-l' + d.name
            else:
                name = d.name
            names.append(name)
        if not names:
            return None
        tpl = msg_many if len(names) > 1 else msg_single
        return tpl.format(', '.join(names)) + endl

    @noPosargs
    @permittedKwargs({})
    def version_method(self, args, kwargs):
        return self.compiler.version

    @noPosargs
    @permittedKwargs({})
    def cmd_array_method(self, args, kwargs):
        return self.compiler.exelist

    def determine_args(self, kwargs, mode='link'):
        nobuiltins = kwargs.get('no_builtin_args', False)
        if not isinstance(nobuiltins, bool):
            raise InterpreterException('Type of no_builtin_args not a boolean.')
        args = []
        incdirs = mesonlib.extract_as_list(kwargs, 'include_directories')
        for i in incdirs:
            from ..build import IncludeDirs
            if not isinstance(i, IncludeDirs):
                raise InterpreterException('Include directories argument must be an include_directories object.')
            for idir in i.to_string_list(self.environment.get_source_dir()):
                args += self.compiler.get_include_args(idir, False)
        if not nobuiltins:
            opts = self.environment.coredata.options
            args += self.compiler.get_option_compile_args(opts)
            if mode == 'link':
                args += self.compiler.get_option_link_args(opts)
        args += mesonlib.stringlistify(kwargs.get('args', []))
        return args

    def determine_dependencies(self, kwargs, endl=':'):
        deps = kwargs.get('dependencies', None)
        if deps is not None:
            final_deps = []
            while deps:
                next_deps = []
                for d in mesonlib.listify(deps):
                    if not isinstance(d, dependencies.Dependency) or d.is_built():
                        raise InterpreterException('Dependencies must be external dependencies')
                    final_deps.append(d)
                    next_deps.extend(d.ext_deps)
                deps = next_deps
            deps = final_deps
        return deps, self._dep_msg(deps, endl)

    @permittedKwargs({
        'prefix',
        'args',
        'dependencies',
    })
    def alignment_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Alignment method takes exactly one positional argument.')
        check_stringlist(args)
        typename = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of alignment must be a string.')
        extra_args = mesonlib.stringlistify(kwargs.get('args', []))
        deps, msg = self.determine_dependencies(kwargs)
        result = self.compiler.alignment(typename, prefix, self.environment,
                                         extra_args=extra_args,
                                         dependencies=deps)
        mlog.log('Checking for alignment of', mlog.bold(typename, True), msg, result)
        return result

    @permittedKwargs({
        'name',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def run_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Run method takes exactly one positional argument.')
        code = args[0]
        if isinstance(code, mesonlib.File):
            code = mesonlib.File.from_absolute_file(
                code.rel_to_builddir(self.environment.source_dir))
        elif not isinstance(code, str):
            raise InvalidArguments('Argument must be string or file.')
        testname = kwargs.get('name', '')
        if not isinstance(testname, str):
            raise InterpreterException('Testname argument must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs, endl=None)
        result = self.compiler.run(code, self.environment, extra_args=extra_args,
                                   dependencies=deps)
        if len(testname) > 0:
            if not result.compiled:
                h = mlog.red('DID NOT COMPILE')
            elif result.returncode == 0:
                h = mlog.green('YES')
            else:
                h = mlog.red('NO (%d)' % result.returncode)
            mlog.log('Checking if', mlog.bold(testname, True), msg, 'runs:', h)
        return result

    @noPosargs
    @permittedKwargs({})
    def get_id_method(self, args, kwargs):
        return self.compiler.get_id()

    @noPosargs
    @permittedKwargs({})
    @FeatureNew('compiler.get_linker_id', '0.53.0')
    def get_linker_id_method(self, args, kwargs):
        return self.compiler.get_linker_id()

    @noPosargs
    @permittedKwargs({})
    def symbols_have_underscore_prefix_method(self, args, kwargs):
        '''
        Check if the compiler prefixes _ (underscore) to global C symbols
        See: https://en.wikipedia.org/wiki/Name_mangling#C
        '''
        return self.compiler.symbols_have_underscore_prefix(self.environment)

    @noPosargs
    @permittedKwargs({})
    def unittest_args_method(self, args, kwargs):
        '''
        This function is deprecated and should not be used.
        It can be removed in a future version of Meson.
        '''
        if not hasattr(self.compiler, 'get_feature_args'):
            raise InterpreterException(f'This {self.compiler.get_display_language()} compiler has no feature arguments.')
        build_to_src = os.path.relpath(self.environment.get_source_dir(), self.environment.get_build_dir())
        return self.compiler.get_feature_args({'unittest': 'true'}, build_to_src)

    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def has_member_method(self, args, kwargs):
        if len(args) != 2:
            raise InterpreterException('Has_member takes exactly two arguments.')
        check_stringlist(args)
        typename, membername = args
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_member must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        had, cached = self.compiler.has_members(typename, [membername], prefix,
                                                self.environment,
                                                extra_args=extra_args,
                                                dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        mlog.log('Checking whether type', mlog.bold(typename, True),
                 'has member', mlog.bold(membername, True), msg, hadtxt, cached)
        return had

    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def has_members_method(self, args, kwargs):
        if len(args) < 2:
            raise InterpreterException('Has_members needs at least two arguments.')
        check_stringlist(args)
        typename, *membernames = args
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_members must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        had, cached = self.compiler.has_members(typename, membernames, prefix,
                                                self.environment,
                                                extra_args=extra_args,
                                                dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        members = mlog.bold(', '.join([f'"{m}"' for m in membernames]))
        mlog.log('Checking whether type', mlog.bold(typename, True),
                 'has members', members, msg, hadtxt, cached)
        return had

    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def has_function_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Has_function takes exactly one argument.')
        check_stringlist(args)
        funcname = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_function must be a string.')
        extra_args = self.determine_args(kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        had, cached = self.compiler.has_function(funcname, prefix, self.environment,
                                                 extra_args=extra_args,
                                                 dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        mlog.log('Checking for function', mlog.bold(funcname, True), msg, hadtxt, cached)
        return had

    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def has_type_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Has_type takes exactly one argument.')
        check_stringlist(args)
        typename = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_type must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        had, cached = self.compiler.has_type(typename, prefix, self.environment,
                                             extra_args=extra_args, dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if had:
            hadtxt = mlog.green('YES')
        else:
            hadtxt = mlog.red('NO')
        mlog.log('Checking for type', mlog.bold(typename, True), msg, hadtxt, cached)
        return had

    @FeatureNew('compiler.compute_int', '0.40.0')
    @permittedKwargs({
        'prefix',
        'low',
        'high',
        'guess',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def compute_int_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Compute_int takes exactly one argument.')
        check_stringlist(args)
        expression = args[0]
        prefix = kwargs.get('prefix', '')
        low = kwargs.get('low', None)
        high = kwargs.get('high', None)
        guess = kwargs.get('guess', None)
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of compute_int must be a string.')
        if low is not None and not isinstance(low, int):
            raise InterpreterException('Low argument of compute_int must be an int.')
        if high is not None and not isinstance(high, int):
            raise InterpreterException('High argument of compute_int must be an int.')
        if guess is not None and not isinstance(guess, int):
            raise InterpreterException('Guess argument of compute_int must be an int.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        res = self.compiler.compute_int(expression, low, high, guess, prefix,
                                        self.environment, extra_args=extra_args,
                                        dependencies=deps)
        mlog.log('Computing int of', mlog.bold(expression, True), msg, res)
        return res

    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def sizeof_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('Sizeof takes exactly one argument.')
        check_stringlist(args)
        element = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of sizeof must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        esize = self.compiler.sizeof(element, prefix, self.environment,
                                     extra_args=extra_args, dependencies=deps)
        mlog.log('Checking for size of', mlog.bold(element, True), msg, esize)
        return esize

    @FeatureNew('compiler.get_define', '0.40.0')
    @permittedKwargs({
        'prefix',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def get_define_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('get_define() takes exactly one argument.')
        check_stringlist(args)
        element = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of get_define() must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        value, cached = self.compiler.get_define(element, prefix, self.environment,
                                                 extra_args=extra_args,
                                                 dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        mlog.log('Fetching value of define', mlog.bold(element, True), msg, value, cached)
        return value

    @permittedKwargs({
        'name',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def compiles_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('compiles method takes exactly one argument.')
        code = args[0]
        if isinstance(code, mesonlib.File):
            code = mesonlib.File.from_absolute_file(
                code.rel_to_builddir(self.environment.source_dir))
        elif not isinstance(code, str):
            raise InvalidArguments('Argument must be string or file.')
        testname = kwargs.get('name', '')
        if not isinstance(testname, str):
            raise InterpreterException('Testname argument must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs, endl=None)
        result, cached = self.compiler.compiles(code, self.environment,
                                                extra_args=extra_args,
                                                dependencies=deps)
        if len(testname) > 0:
            if result:
                h = mlog.green('YES')
            else:
                h = mlog.red('NO')
            cached = mlog.blue('(cached)') if cached else ''
            mlog.log('Checking if', mlog.bold(testname, True), msg, 'compiles:', h, cached)
        return result

    @permittedKwargs({
        'name',
        'no_builtin_args',
        'include_directories',
        'args',
        'dependencies',
    })
    def links_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('links method takes exactly one argument.')
        code = args[0]
        if isinstance(code, mesonlib.File):
            code = mesonlib.File.from_absolute_file(
                code.rel_to_builddir(self.environment.source_dir))
        elif not isinstance(code, str):
            raise InvalidArguments('Argument must be string or file.')
        testname = kwargs.get('name', '')
        if not isinstance(testname, str):
            raise InterpreterException('Testname argument must be a string.')
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs, endl=None)
        result, cached = self.compiler.links(code, self.environment,
                                             extra_args=extra_args,
                                             dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if len(testname) > 0:
            if result:
                h = mlog.green('YES')
            else:
                h = mlog.red('NO')
            mlog.log('Checking if', mlog.bold(testname, True), msg, 'links:', h, cached)
        return result

    @FeatureNew('compiler.check_header', '0.47.0')
    @FeatureNewKwargs('compiler.check_header', '0.50.0', ['required'])
    @permittedKwargs(header_permitted_kwargs)
    def check_header_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('check_header method takes exactly one argument.')
        check_stringlist(args)
        hname = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_header must be a string.')
        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject, default=False)
        if disabled:
            mlog.log('Check usable header', mlog.bold(hname, True), 'skipped: feature', mlog.bold(feature), 'disabled')
            return False
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        haz, cached = self.compiler.check_header(hname, prefix, self.environment,
                                                 extra_args=extra_args,
                                                 dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if required and not haz:
            raise InterpreterException(f'{self.compiler.get_display_language()} header {hname!r} not usable')
        elif haz:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log('Check usable header', mlog.bold(hname, True), msg, h, cached)
        return haz

    @FeatureNewKwargs('compiler.has_header', '0.50.0', ['required'])
    @permittedKwargs(header_permitted_kwargs)
    def has_header_method(self, args, kwargs):
        if len(args) != 1:
            raise InterpreterException('has_header method takes exactly one argument.')
        check_stringlist(args)
        hname = args[0]
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_header must be a string.')
        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject, default=False)
        if disabled:
            mlog.log('Has header', mlog.bold(hname, True), 'skipped: feature', mlog.bold(feature), 'disabled')
            return False
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        haz, cached = self.compiler.has_header(hname, prefix, self.environment,
                                               extra_args=extra_args, dependencies=deps)
        cached = mlog.blue('(cached)') if cached else ''
        if required and not haz:
            raise InterpreterException(f'{self.compiler.get_display_language()} header {hname!r} not found')
        elif haz:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log('Has header', mlog.bold(hname, True), msg, h, cached)
        return haz

    @FeatureNewKwargs('compiler.has_header_symbol', '0.50.0', ['required'])
    @permittedKwargs(header_permitted_kwargs)
    def has_header_symbol_method(self, args, kwargs):
        if len(args) != 2:
            raise InterpreterException('has_header_symbol method takes exactly two arguments.')
        check_stringlist(args)
        hname, symbol = args
        prefix = kwargs.get('prefix', '')
        if not isinstance(prefix, str):
            raise InterpreterException('Prefix argument of has_header_symbol must be a string.')
        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject, default=False)
        if disabled:
            mlog.log(f'Header <{hname}> has symbol', mlog.bold(symbol, True), 'skipped: feature', mlog.bold(feature), 'disabled')
            return False
        extra_args = functools.partial(self.determine_args, kwargs)
        deps, msg = self.determine_dependencies(kwargs)
        haz, cached = self.compiler.has_header_symbol(hname, symbol, prefix, self.environment,
                                                      extra_args=extra_args,
                                                      dependencies=deps)
        if required and not haz:
            raise InterpreterException(f'{self.compiler.get_display_language()} symbol {symbol} not found in header {hname}')
        elif haz:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        cached = mlog.blue('(cached)') if cached else ''
        mlog.log(f'Header <{hname}> has symbol', mlog.bold(symbol, True), msg, h, cached)
        return haz

    def notfound_library(self, libname):
        lib = dependencies.ExternalLibrary(libname, None,
                                           self.environment,
                                           self.compiler.language,
                                           silent=True)
        return lib

    @FeatureNewKwargs('compiler.find_library', '0.51.0', ['static'])
    @FeatureNewKwargs('compiler.find_library', '0.50.0', ['has_headers'])
    @FeatureNewKwargs('compiler.find_library', '0.49.0', ['disabler'])
    @disablerIfNotFound
    @permittedKwargs(find_library_permitted_kwargs)
    def find_library_method(self, args, kwargs):
        # TODO add dependencies support?
        if len(args) != 1:
            raise InterpreterException('find_library method takes one argument.')
        libname = args[0]
        if not isinstance(libname, str):
            raise InterpreterException('Library name not a string.')

        disabled, required, feature = extract_required_kwarg(kwargs, self.subproject)
        if disabled:
            mlog.log('Library', mlog.bold(libname), 'skipped: feature', mlog.bold(feature), 'disabled')
            return self.notfound_library(libname)

        has_header_kwargs = {k[7:]: v for k, v in kwargs.items() if k.startswith('header_')}
        has_header_kwargs['required'] = required
        headers = mesonlib.stringlistify(kwargs.get('has_headers', []))
        for h in headers:
            if not self.has_header_method([h], has_header_kwargs):
                return self.notfound_library(libname)

        search_dirs = extract_search_dirs(kwargs)

        libtype = mesonlib.LibType.PREFER_SHARED
        if 'static' in kwargs:
            if not isinstance(kwargs['static'], bool):
                raise InterpreterException('static must be a boolean')
            libtype = mesonlib.LibType.STATIC if kwargs['static'] else mesonlib.LibType.SHARED
        linkargs = self.compiler.find_library(libname, self.environment, search_dirs, libtype)
        if required and not linkargs:
            if libtype == mesonlib.LibType.PREFER_SHARED:
                libtype = 'shared or static'
            else:
                libtype = libtype.name.lower()
            raise InterpreterException('{} {} library {!r} not found'
                                       .format(self.compiler.get_display_language(),
                                               libtype, libname))
        lib = dependencies.ExternalLibrary(libname, linkargs, self.environment,
                                           self.compiler.language)
        return lib

    @permittedKwargs({})
    def has_argument_method(self, args: T.Sequence[str], kwargs) -> bool:
        args = mesonlib.stringlistify(args)
        if len(args) != 1:
            raise InterpreterException('has_argument takes exactly one argument.')
        return self.has_multi_arguments_method(args, kwargs)

    @permittedKwargs({})
    def has_multi_arguments_method(self, args: T.Sequence[str], kwargs: dict):
        args = mesonlib.stringlistify(args)
        result, cached = self.compiler.has_multi_arguments(args, self.environment)
        if result:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        cached = mlog.blue('(cached)') if cached else ''
        mlog.log(
            'Compiler for {} supports arguments {}:'.format(
                self.compiler.get_display_language(), ' '.join(args)),
            h, cached)
        return result

    @FeatureNew('compiler.get_supported_arguments', '0.43.0')
    @typed_kwargs(
        'compiler.get_supported_arguments',
        KwargInfo('checked', str, default='off', since='0.59.0',
                  validator=lambda s: 'must be one of "warn", "require" or "off"' if s not in ['warn', 'require', 'off'] else None)
    )
    def get_supported_arguments_method(self, args: T.Sequence[str], kwargs: T.Dict[str, T.Any]):
        args = mesonlib.stringlistify(args)
        supported_args = []
        checked = kwargs.pop('checked')

        for arg in args:
            if not self.has_argument_method(arg, kwargs):
                msg = f'Compiler for {self.compiler.get_display_language()} does not support "{arg}"'
                if checked == 'warn':
                    mlog.warning(msg)
                elif checked == 'require':
                    raise mesonlib.MesonException(msg)
            else:
                supported_args.append(arg)
        return supported_args

    @permittedKwargs({})
    def first_supported_argument_method(self, args: T.Sequence[str], kwargs: dict) -> T.List[str]:
        for arg in mesonlib.stringlistify(args):
            if self.has_argument_method(arg, kwargs):
                mlog.log('First supported argument:', mlog.bold(arg))
                return [arg]
        mlog.log('First supported argument:', mlog.red('None'))
        return []

    @FeatureNew('compiler.has_link_argument', '0.46.0')
    @permittedKwargs({})
    def has_link_argument_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        if len(args) != 1:
            raise InterpreterException('has_link_argument takes exactly one argument.')
        return self.has_multi_link_arguments_method(args, kwargs)

    @FeatureNew('compiler.has_multi_link_argument', '0.46.0')
    @permittedKwargs({})
    def has_multi_link_arguments_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        result, cached = self.compiler.has_multi_link_arguments(args, self.environment)
        cached = mlog.blue('(cached)') if cached else ''
        if result:
            h = mlog.green('YES')
        else:
            h = mlog.red('NO')
        mlog.log(
            'Compiler for {} supports link arguments {}:'.format(
                self.compiler.get_display_language(), ' '.join(args)),
            h, cached)
        return result

    @FeatureNew('compiler.get_supported_link_arguments_method', '0.46.0')
    @permittedKwargs({})
    def get_supported_link_arguments_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        supported_args = []
        for arg in args:
            if self.has_link_argument_method(arg, kwargs):
                supported_args.append(arg)
        return supported_args

    @FeatureNew('compiler.first_supported_link_argument_method', '0.46.0')
    @permittedKwargs({})
    def first_supported_link_argument_method(self, args, kwargs):
        for i in mesonlib.stringlistify(args):
            if self.has_link_argument_method(i, kwargs):
                mlog.log('First supported link argument:', mlog.bold(i))
                return [i]
        mlog.log('First supported link argument:', mlog.red('None'))
        return []

    @FeatureNew('compiler.has_function_attribute', '0.48.0')
    @permittedKwargs({})
    def has_func_attribute_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        if len(args) != 1:
            raise InterpreterException('has_func_attribute takes exactly one argument.')
        result, cached = self.compiler.has_func_attribute(args[0], self.environment)
        cached = mlog.blue('(cached)') if cached else ''
        h = mlog.green('YES') if result else mlog.red('NO')
        mlog.log('Compiler for {} supports function attribute {}:'.format(self.compiler.get_display_language(), args[0]), h, cached)
        return result

    @FeatureNew('compiler.get_supported_function_attributes', '0.48.0')
    @permittedKwargs({})
    def get_supported_function_attributes_method(self, args, kwargs):
        args = mesonlib.stringlistify(args)
        return [a for a in args if self.has_func_attribute_method(a, kwargs)]

    @FeatureNew('compiler.get_argument_syntax_method', '0.49.0')
    @noPosargs
    @noKwargs
    def get_argument_syntax_method(self, args, kwargs):
        return self.compiler.get_argument_syntax()
