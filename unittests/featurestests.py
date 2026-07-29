# Copyright (c) 2023, NumPy Developers.

import re
import os
import contextlib
from unittest import mock
from mesonbuild.interpreter import Interpreter
from mesonbuild.build import Build
from mesonbuild.mparser import IdNode, SymbolNode, Token, FunctionNode, ArgumentNode
from mesonbuild.modules import ModuleState
from mesonbuild.modules.features import Module
from mesonbuild.compilers import Compiler, CompileResult
from mesonbuild.mesonlib import MachineChoice
from mesonbuild.envconfig import MachineInfo

from .baseplatformtests import BasePlatformTests
from run_tests import FakeBuild, get_fake_env, get_convincing_fake_env_and_cc

class FakeCompiler(Compiler):
    language = 'c'

    def __init__(self, trap_args = '', trap_code=''):
        super().__init__(
            ccache=[], exelist=[], version='0.0',
            environment=get_fake_env(),
            for_machine=MachineChoice.HOST,
        )
        self.trap_args = trap_args
        self.trap_code = trap_code

    def sanity_check(self, work_dir: str, environment: 'Environment') -> None:
        pass

    def get_optimization_args(self, optimization_level: str) -> 'T.List[str]':
        return []

    def get_output_args(self, outputname: str) -> 'T.List[str]':
        return []

    def has_multi_arguments(self, args: 'T.List[str]') -> 'T.Tuple[bool, bool]':
        if self.trap_args:
            for a in args:
                if re.match(self.trap_args, a):
                    return False, False
        return True, False

    @contextlib.contextmanager
    def compile(self, code: 'mesonlib.FileOrString', *args, **kwargs
               ) -> 'T.Iterator[T.Optional[CompileResult]]':
        if self.trap_code and re.match(self.trap_code, code):
            rcode = -1
        else:
            rcode = 0
        result = CompileResult(
            stdout='',
            stderr='',
            command=[],
            returncode=rcode,
            input_name='fake_input.c'
        )
        yield result

    @contextlib.contextmanager
    def cached_compile(self, code: 'mesonlib.FileOrString', *args, **kwargs
                      ) -> 'T.Iterator[T.Optional[CompileResult]]':
        if self.trap_code and re.match(self.trap_code, code):
            rcode = -1
        else:
            rcode = 0
        result = CompileResult(
            stdout='',
            stderr='',
            command=[],
            returncode=rcode,
            input_name='fake_input.c'
        )
        yield result


    def _sanity_check_source_code(self) -> str:
        return 'public static int main() { return 0; }'

class FeaturesTests(BasePlatformTests):

    @mock.patch.dict(os.environ)
    @mock.patch.object(Interpreter, 'load_root_meson_file', mock.Mock(return_value=None))
    @mock.patch.object(Interpreter, 'sanity_check_ast', mock.Mock(return_value=None))
    @mock.patch.object(Interpreter, 'parse_project', mock.Mock(return_value=None))
    def setUp(self):
        super().setUp()
        env, cc = get_convincing_fake_env_and_cc(
            bdir=self.builddir, prefix=self.prefix)
        env.machines.target = env.machines.host

        # Disable unit test specific syntax
        os.environ.pop('MESON_RUNNING_IN_PROJECT_TESTS', None)
        build = Build(env)
        interp = Interpreter(build)
        # Mock out user_defined_options to bypass the coredata initialization crash
        interp.user_defined_options = mock.Mock()
        interp.user_defined_options.cmd_line_options = {}

        project = interp.funcs['project']
        filename = 'featurestests.py'
        dummy_span = (0, 0) # Safe placeholder for bytespan: Tuple[int, int]
        func_name_token = Token('id', filename, 0, 0, 0, dummy_span, 'FeaturesTests')
        lpar_token = Token('lpar', filename, 0, 0, 13, dummy_span, '(')
        arg_token = Token('string', filename, 0, 0, 14, dummy_span, '')
        rpar_token = Token('rpar', filename, 0, 0, 15, dummy_span, ')')
        node = FunctionNode(
            IdNode(func_name_token),
            SymbolNode(lpar_token),
            ArgumentNode(arg_token),
            SymbolNode(rpar_token)
        )
        project(node, ['Test Module Features'], {'version': '0.1'})
        self.cc = cc
        self.state = ModuleState(interp)
        self.mod_features = Module()

    def clear_cache(self):
        self.mod_features = Module()

    def mod_method(self, name: str, *args, **kwargs):
        mth = self.mod_features.methods.get(name)
        return mth(self.state, list(args), kwargs)

    def mod_new(self, *args, **kwargs):
        return self.mod_method('new', *args, **kwargs)

    def mod_test(self, *args, **kwargs):
        return self.mod_method('test', *args, **kwargs)

    def update_feature(self, feature, **kwargs):
        feature.update_method(self.state, [], kwargs)

    def check_result(self, features, expected_result, anyfet=False, **kwargs):
        is_supported, test_result = self.mod_test(
            *features, compiler=FakeCompiler(**kwargs),
            cached=False, anyfet=anyfet
        )
        test_result = test_result.copy()  # to avoid pop cached dict
        test_result.pop('fail_reason')
        self.assertEqual(is_supported, expected_result['is_supported'])
        self.assertEqual(test_result, expected_result)

    def gen_basic_result(self, prevalent, predecessor=[]):
        prevalent_names = [fet.name for fet in prevalent]
        predecessor_names = [fet.name for fet in predecessor]
        features_names = predecessor_names + prevalent_names
        return {
            'target_name': '__'.join(prevalent_names),
            'prevalent_features': prevalent_names,
            'features': features_names,
            'args': [f'arg{i}' for i in range(1, len(features_names) + 1)],
            'detect': features_names,
            'defines': features_names,
            'undefines': [],
            'is_supported': True,
            'is_disabled': False
        }

    def gen_fail_result(self, prevalent, is_supported=False,
                        is_disabled = False):
        prevalent_names = [fet.name for fet in prevalent]
        return {
            'target_name': '__'.join(prevalent_names),
            'prevalent_features': prevalent_names,
            'features': [],
            'args': [],
            'detect': [],
            'defines': [],
            'undefines': [],
            'is_supported': is_supported,
            'is_disabled': is_disabled
        }

    def test_happy_path(self):
        fet1 = self.mod_new('fet1', 1, args='arg1', test_code='test1')
        fet2 = self.mod_new('fet2', 2, implies=fet1, args='arg2', test_code='test2')
        fet3 = self.mod_new('fet3', 3, implies=fet2, args='arg3')
        fet4 = self.mod_new('fet4', 4, implies=fet3, args='arg4', test_code='test4')
        # fet5 doesn't imply fet4 so we can test target with muti prevalent features
        fet5 = self.mod_new('fet5', 5, implies=fet3, args='arg5')
        fet6 = self.mod_new('fet6', 6, implies=[fet4, fet5], args='arg6')

        # basic test expected the compiler support all operations
        for test_features, prevalent, predecessor in [
            ([fet1], [fet1], []),
            ([fet2], [fet2], [fet1]),
            ([fet2, fet1], [fet2], [fet1]),
            ([fet3], [fet3], [fet1, fet2]),
            ([fet2, fet3, fet1], [fet3], [fet1, fet2]),
            ([fet4, fet5], [fet4, fet5], [fet1, fet2, fet3]),
            ([fet5, fet4], [fet4, fet5], [fet1, fet2, fet3]),
            ([fet6], [fet6], [fet1, fet2, fet3, fet4, fet5]),
        ]:
            expected = self.gen_basic_result(prevalent, predecessor)
            self.check_result(test_features, expected)

        for test_features, prevalent, trap_args in [
            ([fet1], [fet1], 'arg1'),
            ([fet1], [fet1], 'arg1'),
        ]:
            expected = self.gen_fail_result(prevalent)
            self.check_result(test_features, expected, trap_args=trap_args)

    def test_failures(self):
        fet1 = self.mod_new('fet1', 1, args='arg1', test_code='test1')
        fet2 = self.mod_new('fet2', 2, implies=fet1, args='arg2', test_code='test2')
        fet3 = self.mod_new('fet3', 3, implies=fet2, args='arg3', test_code='test3')
        fet4 = self.mod_new('fet4', 4, implies=fet3, args='arg4', test_code='test4')
        # fet5 doesn't imply fet4 so we can test target with muti features
        fet5 = self.mod_new('fet5', 5, implies=fet3, args='arg5', test_code='test5')

        for test_features, prevalent, disable, trap_args, trap_code in [
            # test by trap flags
            ([fet1], [fet1], None, 'arg1', None),
            ([fet2], [fet2], None, 'arg1', None),
            ([fet2, fet1], [fet2], None, 'arg2', None),
            ([fet3], [fet3], None, 'arg1', None),
            ([fet3, fet2], [fet3], None, 'arg2', None),
            ([fet3, fet1], [fet3], None, 'arg3', None),
            ([fet3, fet1], [fet3], None, 'arg3', None),
            ([fet5, fet4], [fet4, fet5], None, 'arg4', None),
            ([fet5, fet4], [fet4, fet5], None, 'arg5', None),
            # test by trap test_code
            ([fet1], [fet1], None, None, 'test1'),
            ([fet2], [fet2], None, None, 'test1'),
            ([fet2, fet1], [fet2], None, None, 'test2'),
            ([fet3], [fet3], None, None, 'test1'),
            ([fet3, fet2], [fet3], None, None, 'test2'),
            ([fet3, fet1], [fet3], None, None, 'test3'),
            ([fet5, fet4], [fet4, fet5], None, None, 'test4'),
            ([fet5, fet4], [fet4, fet5], None, None, 'test5'),
            # test by disable feature
            ([fet1], [fet1], fet1, None, None),
            ([fet2], [fet2], fet1, None, None),
            ([fet2, fet1], [fet2], fet2, None, None),
            ([fet3], [fet3], fet1, None, None),
            ([fet3, fet2], [fet3], fet2, None, None),
            ([fet3, fet1], [fet3], fet3, None, None),
            ([fet5, fet4], [fet4, fet5], fet4, None, None),
            ([fet5, fet4], [fet4, fet5], fet5, None, None),
        ]:
            if disable:
                self.update_feature(disable, disable='test disable')
            expected = self.gen_fail_result(prevalent, is_disabled=not not disable)
            self.check_result(test_features, expected, trap_args=trap_args, trap_code=trap_code)

    def test_any(self):
        fet1 = self.mod_new('fet1', 1, args='arg1', test_code='test1')
        fet2 = self.mod_new('fet2', 2, implies=fet1, args='arg2', test_code='test2')
        fet3 = self.mod_new('fet3', 3, implies=fet2, args='arg3', test_code='test3')
        fet4 = self.mod_new('fet4', 4, implies=fet3, args='arg4', test_code='test4')
        # fet5 doesn't imply fet4 so we can test target with muti features
        fet5 = self.mod_new('fet5', 5, implies=fet3, args='arg5', test_code='test5')
        fet6 = self.mod_new('fet6', 6, implies=[fet4, fet5], args='arg6')

        for test_features, prevalent, predecessor, trap_args in [
            ([fet2], [fet1], [], 'arg2'),
            ([fet6], [fet2], [fet1], 'arg3'),
            ([fet6], [fet4], [fet1, fet2, fet3], 'arg5'),
            ([fet5, fet4], [fet3], [fet1, fet2], 'arg4|arg5'),
        ]:
            expected = self.gen_basic_result(prevalent, predecessor)
            self.check_result(test_features, expected, trap_args=trap_args, anyfet=True)

    def test_conflict_args(self):
        fet1 = self.mod_new('fet1', 1, args='arg1', test_code='test1')
        fet2 = self.mod_new('fet2', 2, implies=fet1, args='arg2', test_code='test2')
        fet3 = self.mod_new('fet3', 3, implies=fet2, args='arg3')
        fet4 = self.mod_new('fet4', 4, implies=fet3, args='arg4', test_code='test4')
        fet5 = self.mod_new('fet5', 5, implies=fet3, args='arg5', test_code='test5')
        fet6 = self.mod_new('fet6', 6, implies=[fet4, fet5], args='arch=xx')

        compiler = FakeCompiler()
        for implies, attr, val, expected_vals in [
            (
                [fet3, fet4, fet5],
                'args', {'val':'arch=the_arch', 'match': 'arg.*'},
                ['arch=the_arch'],
            ),
            (
                [fet5, fet4],
                'args', {'val':'arch=', 'match': 'arg.*', 'mfilter': '[0-9]'},
                ['arch=12345'],
            ),
            (
                [fet5, fet4],
                'args', {'val':'arch=', 'match': 'arg.*', 'mfilter': '[0-9]', 'mjoin': '+'},
                ['arch=1+2+3+4+5'],
            ),
            (
                [fet5, fet4],
                'args', {'val':'arch=num*', 'match': 'arg.*[0-3]', 'mfilter': '[0-9]', 'mjoin': '*'},
                ['arg4', 'arg5', 'arch=num*1*2*3'],
            ),
            (
                [fet6],
                'args', {'val':'arch=', 'match': 'arg.*[0-9]|arch=.*', 'mfilter': r'([0-9])|arch=(\w+)', 'mjoin': '*'},
                ['arch=1*2*3*4*5*xx'],
            ),
            (
                [fet3, fet4, fet5],
                'detect', {'val':'test_fet', 'match': 'fet.*[0-5]'},
                ['test_fet'],
            ),
            (
                [fet5, fet4],
                'detect', {'val':'fet', 'match': 'fet.*[0-5]', 'mfilter': '[0-9]'},
                ['fet12345'],
            ),
            (
                [fet5, fet4],
                'detect', {'val':'fet_', 'match': 'fet.*[0-5]', 'mfilter': '[0-9]', 'mjoin':'_'},
                ['fet_1_2_3_4_5'],
            ),
        ]:
            test_fet = self.mod_new('test_fet', 7, implies=implies, **{attr:val})
            is_supported, test_result = self.mod_test(
                test_fet, compiler=compiler, cached=False
            )
            self.assertEqual(test_result['is_supported'], True)
            self.assertEqual(test_result[attr], expected_vals)

