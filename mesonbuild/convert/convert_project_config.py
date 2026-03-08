#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import itertools

from mesonbuild.convert.common_defs import (
    SelectKind,
    SelectId,
    SelectInstance,
    CustomSelect,
    MesonOptionInstance,
    ProjectOptionsInstance,
)
from mesonbuild.convert.abstract.abstract_dependencies import (
    AbstractDependencies, )
from mesonbuild.convert.convert_project_instance import ConvertProjectInstance


class ConvertProjectConfig:
    """Holds data that remains static across meson convert invocations (dependencies, user-project details)"""

    def __init__(
        self,
        config_data: T.Dict[str, T.Any],
        dependencies: AbstractDependencies,
    ):
        self._toml_data = config_data
        self.dependencies = dependencies

    @property
    def build_system(self) -> str:
        return T.cast(str, self._toml_data.get('project', {}).get('build_system', ''))

    @property
    def project_name(self) -> str:
        return T.cast(str, self._toml_data.get('project', {}).get('project_name', ''))

    @property
    def copyright(self) -> T.Dict[str, T.Any]:
        return T.cast(T.Dict[str, T.Any], self._toml_data.get('copyright', {}))

    @property
    def custom_target(self) -> T.Dict[str, T.Any]:
        return T.cast(T.Dict[str, T.Any], self._toml_data.get('custom_target', {}))

    @property
    def target_renames(self) -> T.Dict[str, str]:
        return T.cast(T.Dict[str, str], self._toml_data.get('target_renames', {}))

    def _get_option_combinations(
        self,
        static_options: T.Dict[str, T.Any],
        variable_options: T.Dict[str, T.List[T.Any]],
    ) -> T.List[ProjectOptionsInstance]:
        """
        Computes the Cartesian product of all variable Meson options.

        This function takes the `variable_options` defined in the TOML
        configuration and generates all possible unique combinations of them. Each
        combination results in a distinct `ProjectOptionsInstance`, which includes
        the fully resolved set of Meson options and the corresponding
        `SelectInstance`s that define that specific configuration variant. This
        allows the tool to analyze each permutation of the build configuration
        independently.
        """
        options: T.List[ProjectOptionsInstance] = []
        custom_selects = self.get_all_custom_selects()
        if not custom_selects:
            options.append(ProjectOptionsInstance(static_options, []))
            return options

        if not variable_options:
            meson_options = static_options.copy()
            select_instances: T.List[SelectInstance] = []
            for select in custom_selects:
                select_instances.append(SelectInstance(select.select_id, select.default_value))

            options.append(ProjectOptionsInstance(meson_options, select_instances))
            return options

        # Get all instances of the Meson project.
        #
        # Input TOML:
        #  - [config.variable_options]
        #    meson_opt_x = [
        #        { true, "project:opt_a=val1" }
        #        { false, "project:opt_a=val2" }
        #    ]
        #    meson_opt_y = [
        #        { true, "project:opt_b=val3" }
        #        { false, "project:opt_b=val4" }
        #    ]
        #
        # Output:
        #  - ProjectOptionsInstance:
        #        meson_options:
        #           {meson_opt_x = true, meson_opt_y = true }
        #        select_instances:
        #           {project_opt_a = val1, project_opt_b = val3 }
        #  - ProjectOptionsInstance:
        #        meson_options:
        #           {meson_opt_x = true, meson_opt_b = false }
        #        select_instances:
        #           {project_opt_a = val1, project_opt_b = val4 }
        #
        #    (...)
        all_instances: T.List[T.List[MesonOptionInstance]] = []
        for option_name, variants in variable_options.items():
            opt_instances: T.List[MesonOptionInstance] = []
            for variant in variants:
                meson_value = variant['value']
                select_string = variant['select']
                opt_instances.append(
                    MesonOptionInstance(
                        option_name,
                        meson_value,
                        SelectInstance.parse_from_string(select_string),
                    ))

            all_instances.append(opt_instances)

        custom_select_ids: T.Dict[SelectId, CustomSelect] = {}
        for select in custom_selects:
            custom_select_ids[select.select_id] = select

        all_instances_product = list(itertools.product(*all_instances))
        for instance_set in all_instances_product:
            meson_options = static_options.copy()
            missing_select_ids = custom_select_ids.copy()
            select_instances_loop: T.List[SelectInstance] = []
            for opt_instance in instance_set:
                meson_options[opt_instance.meson_option] = opt_instance.meson_value
                select_instances_loop.append(opt_instance.select_instance)
                if opt_instance.select_instance.select_id in missing_select_ids:
                    missing_select_ids.pop(opt_instance.select_instance.select_id)

            for select in missing_select_ids.values():
                select_instances_loop.append(SelectInstance(select.select_id, select.default_value))

            options.append(ProjectOptionsInstance(meson_options, select_instances_loop))

        return options

    def get_project_instances(self) -> T.List[ConvertProjectInstance]:
        configs = self._toml_data.get('config', [])
        instances = []

        for config in configs:
            config_name = config.get('config_name', '')
            toolchains_data = config.get('toolchains', {})
            host_toolchains = toolchains_data.get('host_toolchains', [])
            build_toolchains = toolchains_data.get('build_toolchains', [])
            static_options = config.get('static_options', {}).copy()
            variable_options = config.get('variable_options', {})

            combinations = self._get_option_combinations(static_options, variable_options)

            for host_toolchain in host_toolchains:
                for build_toolchain in build_toolchains:
                    for combo in combinations:
                        instances.append(
                            ConvertProjectInstance(
                                name=config_name,
                                host_toolchain=host_toolchain,
                                build_toolchain=build_toolchain,
                                option_instance=combo,
                            ))

        return instances

    def get_all_custom_selects(self) -> T.List[CustomSelect]:
        custom_vars_data = self._toml_data.get('custom_variable', [])
        return [
            CustomSelect(
                select_id=SelectId(
                    select_kind=SelectKind.CUSTOM,
                    namespace=select_data.get('namespace', ''),
                    variable=select_data.get('name', ''),
                ),
                possible_values=select_data.get('possible_values', []),
                default_value=select_data.get('default_value', ''),
            ) for select_data in custom_vars_data
        ]

    def is_dependency_necessary(self, dep_name: str) -> bool:
        # Common libraries usually apart of the libc implementation
        return dep_name not in ['threads', 'm', 'dl', 'c', 'rt']

    def sanitize_target_name(self, target_name: str) -> str:
        if target_name in self.target_renames:
            return self.target_renames[target_name]
        return target_name.translate(str.maketrans('', '', '[]'))
