# Copyright (c) 2023, NumPy Developers.
# All rights reserved.

import typing as T
import os

from ... import mlog, build
from ...compilers import Compiler
from ...mesonlib import File, MesonException
from ...interpreter.type_checking import NoneType
from ...interpreterbase.decorators import (
    noKwargs, noPosargs, KwargInfo, typed_kwargs, typed_pos_args,
    ContainerTypeInfo, permittedKwargs
)
from .. import ModuleInfo, NewExtensionModule, ModuleReturnValue
from .feature import FeatureObject, ConflictAttr
from .utils import test_code, get_compiler

if T.TYPE_CHECKING:
    from typing import TypedDict
    from ...interpreterbase import TYPE_var, TYPE_kwargs
    from .. import ModuleState
    from .feature import FeatureKwArgs

    class TestKwArgs(TypedDict):
        compiler: T.Optional[Compiler]
        force_args: T.Optional[T.List[str]]
        any: T.Optional[bool]

class Module(NewExtensionModule):
    INFO = ModuleInfo('feature', '0.1.0')

    def __init__(self) -> None:
        super().__init__()
        self.methods.update({
            'new': self.new_method,
            'test': self.test_method,
            'implicit': self.implicit_method,
            'implicit_c': self.implicit_c_method,
            'sort': self.sort_method,
            'multi_target': self.multi_target_method,
        })
        # TODO: How to store and load from files in meson?
        self.cached_tests = {}

    def new_method(self, state: 'ModuleState',
                   args: T.List['TYPE_var'],
                   kwargs: 'TYPE_kwargs') -> FeatureObject:
        return FeatureObject(state, args, kwargs)

    @typed_pos_args('feature.test', varargs=FeatureObject, min_varargs=1)
    @typed_kwargs('feature.test',
        KwargInfo('compiler', (NoneType, Compiler)),
        KwargInfo('anyfet', bool, default = False),
        KwargInfo(
            'force_args', (NoneType, str, ContainerTypeInfo(list, str)),
            listify=True
        ),
    )
    def test_method(self, state: 'ModuleState',
                    args: T.Tuple[T.List[FeatureObject]],
                    kwargs: 'TestKwArgs'
                    ) -> T.List[T.Union[bool, T.Dict[str, T.Any]]]:

        features = args[0]
        features_set = set(features)
        anyfet = kwargs['anyfet']
        compiler = kwargs.get('compiler')
        if not compiler:
            compiler = get_compiler(state)

        force_args = kwargs['force_args']
        if force_args is not None:
            # removes in empty strings
            force_args = [a for a in force_args if a]

        cached, test_result = self.test(
            state, features=features_set,
            compiler=compiler,
            anyfet=anyfet,
            force_args=force_args
        )
        if not test_result['is_supported']:
            if test_result['is_disabled']:
                label = mlog.yellow('disabled')
            else:
                label = mlog.yellow('Unsupported')
        else:
            label = mlog.green('Supported')
            if anyfet:
                unsupported = [
                    fet.name for fet in sorted(features_set)
                    if fet.name not in test_result['features']
                ]
                if unsupported:
                    unsupported = ' '.join(unsupported)
                    label = mlog.green(f'Parial support, missing({unsupported})')

        features_names = ' '.join([f.name for f in features])
        log_prefix = f'Test features "{mlog.bold(features_names)}" :'
        cached_msg = f'({mlog.blue("cached")})' if cached else ''
        if not test_result['is_supported']:
            mlog.log(log_prefix, label, 'due to', test_result['fail_reason'])
        else:
            mlog.log(log_prefix, label, cached_msg)
        return [test_result['is_supported'], test_result]

    def test(self, state, features: T.Set[FeatureObject],
             compiler: 'Compiler',
             anyfet: bool = False,
             force_args: T.Optional[T.Tuple[str]] = None,
             _caller: T.Set[FeatureObject] = set()
             ) -> T.Tuple[bool, T.Dict[str, T.Union[str, T.List[str]]]]:
        # cached hash should inveolov all implied features
        # since FeatureObject is mutable object.
        implied_features = self.implicit(features)
        test_hash = hash((
            tuple(sorted(features)),
            tuple(sorted(implied_features)),
            compiler, anyfet,
            (-1 if force_args is None else tuple(force_args))
        ))
        result = self.cached_tests.get(test_hash)
        if result is not None:
            return True, result

        all_features = sorted(implied_features.union(features))
        if anyfet:
            cached, test_result = self.test(
                state, features=features,
                compiler=compiler,
                force_args=force_args
            )
            if test_result['is_supported']:
                self.cached_tests[test_hash] = test_result
                return False, test_result

            features_any = set()
            for fet in all_features:
                _, test_result = self.test(
                    state, features={fet,},
                    compiler=compiler,
                    force_args=force_args
                )
                if test_result['is_supported']:
                    features_any.add(fet)

            _, test_result = self.test(
                state, features=features_any,
                compiler=compiler,
                force_args=force_args
            )
            self.cached_tests[test_hash] = test_result
            return False, test_result

        # For multiple features, it important to erase any features
        # implied by another to avoid duplicate testing since
        # implied already tested also we use this set to genrate
        # unque target name that can be used for multiple targets
        # build.
        prevalent_features = features.difference(implied_features)
        if len(prevalent_features) == 0:
            # It happens when all features imply each other.
            # Set the highest interested feature
            prevalent_features = sorted(features)[-1:]
        else:
            prevalent_features = sorted(prevalent_features)

        prevalent_names = [fet.name for fet in prevalent_features]
        # prepare the result dict
        test_result = {
            'target_name': '__'.join(prevalent_names),
            'prevalent_features': prevalent_names,
            'features': [fet.name for fet in all_features],
            'args': [],
            'detect': [],
            'defines': [],
            'undefines': [],
            'is_supported': True,
            'is_disabled': False,
            'fail_reason': '',
        }
        def fail_result(fail_reason, is_disabled = False,
                        result_dict = test_result.copy()):
            result_dict.update({
                'is_supported': False,
                'is_disabled': is_disabled,
                'fail_reason': fail_reason,
                'features': []
            })
            self.cached_tests[test_hash] = result_dict
            return False, result_dict

        # since we allows features to imply each other
        # items of `features` may part of `implied_features`
        _caller = _caller.union(prevalent_features)
        predecessor_features = implied_features.difference(_caller)
        for fet in sorted(predecessor_features):
            _, pred_result = self.test(
                state, features={fet,},
                compiler=compiler,
                force_args=force_args,
                _caller=_caller
            )
            if not pred_result['is_supported']:
                reason = f'Implied feature "{fet.name}" '
                pred_disabled = pred_result['is_disabled']
                if pred_disabled:
                   fail_reason = reason + 'is disabled'
                else:
                   fail_reason = reason + 'is not supported'
                return fail_result(fail_reason, pred_disabled)

            for k in ['defines', 'undefines']:
                values = test_result[k]
                pred_values = pred_result[k]
                values += [v for v in pred_values if v not in values]

        # Sort based on the lowest interest to deal with conflict attributes
        # when combine all attributes togathers
        conflict_attrs = ['detect']
        if force_args is None:
            conflict_attrs += ['args']
        else:
            test_result['args'] = force_args

        for fet in all_features:
            for attr in conflict_attrs:
                values: T.List[ConflictAttr] = getattr(fet, attr)
                accumulate_values = test_result[attr]
                for conflict in values:
                    conflict_val: str = conflict.val
                    if not conflict.match:
                        accumulate_values.append(conflict_val)
                        continue
                    # select the acc items based on the match
                    new_acc: T.List[str] = []
                    for acc in accumulate_values:
                        # not affected by the match so we keep it
                        if not conflict.match.match(acc):
                            new_acc.append(acc)
                            continue
                        # no filter so we totaly escape it
                        if not conflict.mfilter:
                            continue
                        filter_val = conflict.mfilter.findall(acc)
                        # no filter match so we totaly escape it
                        if not filter_val:
                            continue
                        conflict_val += conflict.mjoin.join(filter_val)
                    new_acc.append(conflict_val)
                    test_result[attr] = new_acc

        test_args = compiler.has_multi_arguments
        args = test_result['args']
        if args:
            supported_args, test_cached = test_args(args, state.environment)
            if not supported_args:
                return fail_result(
                    f'Arguments "{", ".join(args)}" are not supported'
                )

        for fet in prevalent_features:
            if fet.disable:
                return fail_result(
                    f'{fet.name} is disabled due to "{fet.disable}"',
                    fet.disable
                )

            if fet.test_code:
                _, tested_code, _ = test_code(
                    state, compiler, args, fet.test_code
                )
                if not tested_code:
                    return fail_result(
                        f'Compiler fails against the test code of "{fet.name}"'
                    )

            test_result['defines'] += [fet.name] + fet.group
            for extra_name, extra_test in fet.extra_tests.items():
                _, tested_code, _ = test_code(
                    state, compiler, args, extra_test
                )
                k = 'defines' if tested_code else 'undefines'
                test_result[k].append(extra_name)

        self.cached_tests[test_hash] = test_result
        return False, test_result

    @permittedKwargs(build.known_stlib_kwargs | {
        'dispatch', 'baseline', 'prefix'
    })
    @typed_pos_args('feature.multi_target', str, varargs=(
        str, File, build.CustomTarget, build.CustomTargetIndex,
        build.GeneratedList, build.StructuredSources, build.ExtractedObjects,
        build.BuildTarget
    ))
    @typed_kwargs('feature.multi_target',
        KwargInfo(
            'dispatch', ContainerTypeInfo(list,
                (FeatureObject, list)
            ),
            default=[]
        ),
        KwargInfo(
            'baseline', (NoneType, ContainerTypeInfo(list, FeatureObject))
        ),
        KwargInfo('prefix', str, default=''),
        KwargInfo('compiler', (NoneType, Compiler)),
        allow_unknown=True
    )
    def multi_target_method(self, state: 'ModuleState',
                            args: T.Tuple[str], kwargs: 'TYPE_kwargs'
                            ) -> T.List[T.Union[T.Dict[str, str], T.Any]]:
        config_name = args[0]
        sources = args[1]
        dispatch = kwargs.pop('dispatch')
        baseline = kwargs.pop('baseline')
        prefix = kwargs.pop('prefix')
        compiler = kwargs.pop('compiler')
        if not compiler:
            compiler = get_compiler(state)

        info = {}
        if baseline is not None:
            baseline_features = self.implicit_c(baseline)
            cached, baseline = self.test(
                state, features=set(baseline), anyfet=True,
                compiler=compiler
            )
            info['BASELINE'] = baseline
        else:
            baseline_features = []

        dispatch_tests = []
        for d in dispatch:
            if isinstance(d, FeatureObject):
                target = {d,}
                is_base_part = d in baseline_features
            else:
                target = set(d)
                is_base_part = all([f in baseline_features for f in d])
            if is_base_part:
                # TODO: add log
                continue
            cached, test_result = self.test(
                state, features=target,
                compiler=compiler
            )
            if not test_result['is_supported']:
                continue
            target_name = test_result['target_name']
            if target_name in info:
                continue
            info[target_name] = test_result
            dispatch_tests.append(test_result)

        dispatch_calls = []
        for test_result in dispatch_tests:
            detect = '&&'.join([
                f'TEST_CB({d})' for d in test_result['detect']
            ])
            if detect:
                detect = f'({detect})'
            else:
                detect = '1'
            target_name = test_result['target_name']
            dispatch_calls.append(
                f'{prefix}_MTARGETS_EXPAND('
                    f'EXEC_CB({detect}, {target_name}, __VA_ARGS__)'
                ')'
            )

        config_file = [
            '/* Autogenerated by the Meson features module. */',
            '/* Do not edit, your changes will be lost. */',
            '',
            f'#undef {prefix}_MTARGETS_EXPAND',
            f'#define {prefix}_MTARGETS_EXPAND(X) X',
            '',
            f'#undef {prefix}MTARGETS_CONF_BASELINE',
            f'#define {prefix}MTARGETS_CONF_BASELINE(EXEC_CB, ...) ' + (
                f'{prefix}_MTARGETS_EXPAND(EXEC_CB(__VA_ARGS__))'
                if baseline is not None
                else ''
            ),
            '',
            f'#undef {prefix}MTARGETS_CONF_DISPATCH',
            f'#define {prefix}MTARGETS_CONF_DISPATCH(TEST_CB, EXEC_CB, ...) \\',
            ' \\\n'.join(dispatch_calls),
            '',
        ]

        src_dir = state.environment.source_dir
        sub_dir = state.subdir
        if sub_dir:
            src_dir = os.path.join(src_dir, state.subdir)
        config_path = os.path.abspath(os.path.join(src_dir, config_name))

        mlog.log(
            "Generating", config_name, 'into path', config_path,
            "based on the specifed targets"
        )
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding='utf-8') as cout:
            cout.write('\n'.join(config_file))

        static_libs = []
        if baseline:
            static_libs.append(self.gen_target(
                state, config_name, sources,
                baseline, prefix, True, kwargs
            ))

        for test_result in dispatch_tests:
            static_libs.append(self.gen_target(
                state, config_name, sources,
                test_result, prefix,
                False, kwargs
            ))
        return [info, static_libs]

    def gen_target(self, state, config_name, sources,
                   test_result, prefix,
                   is_baseline, stlib_kwargs):
        target_name = 'baseline' if is_baseline else test_result['target_name']
        args = [f'-D{prefix}HAVE_{df}' for df in test_result['defines']]
        args += test_result['args']
        if is_baseline:
            args.append(f'-D{prefix}MTARGETS_BASELINE')
        else:
            args.append(f'-D{prefix}MTARGETS_CURRENT={target_name}')
        stlib_kwargs = stlib_kwargs.copy()
        stlib_kwargs.update({
            'sources': sources,
            'c_args': stlib_kwargs.get('c_args', []) + args,
            'cpp_args': stlib_kwargs.get('cpp_args', []) + args
        })
        static_lib = state._interpreter.func_static_lib(
            None, [config_name + '_' + target_name],
            stlib_kwargs
        )
        return static_lib

    @typed_pos_args('feature.sort', varargs=FeatureObject, min_varargs=1)
    @typed_kwargs('feature.sort',
        KwargInfo('reverse', bool, default = False),
    )
    def sort_method(self, state: 'ModuleState',
                    args: T.Tuple[T.List[FeatureObject]],
                    kwargs: 'TYPE_kwargs'
                    ) -> T.List[FeatureObject]:
        return sorted(args[0], reverse=kwargs['reverse'])

    @typed_pos_args('feature.implicit', varargs=FeatureObject, min_varargs=1)
    @noKwargs
    def implicit_method(self, state: 'ModuleState',
                        args: T.Tuple[T.List[FeatureObject]],
                        kwargs: 'TYPE_kwargs'
                        ) -> T.List[FeatureObject]:

        features = args[0]
        return sorted(self.implicit(features))

    @typed_pos_args('feature.implicit', varargs=FeatureObject, min_varargs=1)
    @noKwargs
    def implicit_c_method(self, state: 'ModuleState',
                          args: T.Tuple[T.List[FeatureObject]],
                          kwargs: 'TYPE_kwargs'
                          ) -> T.List[FeatureObject]:
        return sorted(self.implicit_c(args[0]))

    @staticmethod
    def implicit(features: T.Sequence[FeatureObject]) -> T.Set[FeatureObject]:
        implies = set().union(*[f.get_implicit() for f in features])
        return implies

    @staticmethod
    def implicit_c(features: T.Sequence[FeatureObject]) -> T.Set[FeatureObject]:
        return Module.implicit(features).union(features)

