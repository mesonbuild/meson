# SPDX-License-Identifier: Apache-2.0
# Copyright 2024 Meson project contributors

from mesonbuild.options import *
from mesonbuild.envconfig import MachineInfo

import os
import unittest


def make_machine(system: str) -> MachineInfo:
    return MachineInfo(system, 'x86_64', 'x86_64', 'little', None, None)


def num_options(store: OptionStore) -> int:
    return len(store.options)


class OptionTests(unittest.TestCase):

    def test_basic(self):
        optstore = OptionStore(False)
        name = 'someoption'
        default_value = 'somevalue'
        new_value = 'new_value'
        vo = UserStringOption(name, 'An option of some sort', default_value)
        optstore.add_system_option(name, vo)
        self.assertEqual(optstore.get_value_for(name), default_value)
        optstore.set_option(OptionKey.from_string(name), new_value)
        self.assertEqual(optstore.get_value_for(name), new_value)

    def test_toplevel_project(self):
        optstore = OptionStore(False)
        name = 'someoption'
        default_value = 'somevalue'
        new_value = 'new_value'
        k = OptionKey(name)
        vo = UserStringOption(k.name, 'An option of some sort', default_value)
        optstore.add_system_option(k.name, vo)
        self.assertEqual(optstore.get_value_for(k), default_value)
        optstore.initialize_from_top_level_project_call({OptionKey('someoption'): new_value}, {}, {})
        self.assertEqual(optstore.get_value_for(k), new_value)

    def test_machine_vs_project(self):
        optstore = OptionStore(False)
        name = 'backend'
        default_value = 'ninja'
        proj_value = 'xcode'
        mfile_value = 'vs2010'
        k = OptionKey(name)
        prefix = UserStringOption('prefix', 'This is needed by OptionStore', '/usr')
        optstore.add_system_option('prefix', prefix)
        vo = UserStringOption(k.name, 'You know what this is', default_value)
        optstore.add_system_option(k.name, vo)
        self.assertEqual(optstore.get_value_for(k), default_value)
        optstore.initialize_from_top_level_project_call({OptionKey(name): proj_value}, {},
                                                        {OptionKey(name): mfile_value})
        self.assertEqual(optstore.get_value_for(k), mfile_value)

    def test_subproject_system_option(self):
        """Test that subproject system options get their default value from the global
           option (e.g. "sub:b_lto" can be initialized from "b_lto")."""
        optstore = OptionStore(False)
        name = 'b_lto'
        default_value = 'false'
        new_value = 'true'
        k = OptionKey(name)
        subk = k.evolve(subproject='sub')
        optstore.initialize_from_top_level_project_call({}, {}, {OptionKey(name): new_value})
        vo = UserStringOption(k.name, 'An option of some sort', default_value)
        optstore.add_system_option(subk, vo)
        self.assertEqual(optstore.get_value_for(subk), new_value)

    def test_parsing(self):
        with self.subTest('subproject'):
            s1 = OptionKey.from_string('sub:optname')
            s1_expected = OptionKey('optname', 'sub', MachineChoice.HOST)
            self.assertEqual(s1, s1_expected)
            self.assertEqual(str(s1), 'sub:optname')

        with self.subTest('plain name'):
            s2 = OptionKey.from_string('optname')
            s2_expected = OptionKey('optname', None, MachineChoice.HOST)
            self.assertEqual(s2, s2_expected)
            self.assertEqual(str(s2), 'optname')

        with self.subTest('root project'):
            s3 = OptionKey.from_string(':optname')
            s3_expected = OptionKey('optname', '', MachineChoice.HOST)
            self.assertEqual(s3, s3_expected)
            self.assertEqual(str(s3), ':optname')

    def test_subproject_for_system(self):
        optstore = OptionStore(False)
        name = 'someoption'
        default_value = 'somevalue'
        vo = UserStringOption(name, 'An option of some sort', default_value)
        optstore.add_system_option(name, vo)
        self.assertEqual(optstore.get_value_for(name, 'somesubproject'), default_value)

    def test_reset(self):
        optstore = OptionStore(False)
        name = 'someoption'
        original_value = 'original'
        reset_value = 'reset'
        vo = UserStringOption(name, 'An option set twice', original_value)
        optstore.add_system_option(name, vo)
        self.assertEqual(optstore.get_value_for(name), original_value)
        self.assertEqual(num_options(optstore), 1)
        vo2 = UserStringOption(name, 'An option set twice', reset_value)
        optstore.add_system_option(name, vo2)
        self.assertEqual(optstore.get_value_for(name), original_value)
        self.assertEqual(num_options(optstore), 1)

    def test_project_nonyielding(self):
        optstore = OptionStore(False)
        name = 'someoption'
        top_value = 'top'
        sub_value = 'sub'
        vo = UserStringOption(name, 'A top level option', top_value, False)
        optstore.add_project_option(OptionKey(name, ''), vo)
        self.assertEqual(optstore.get_value_for(name, ''), top_value, False)
        self.assertEqual(num_options(optstore), 1)
        vo2 = UserStringOption(name, 'A subproject option', sub_value)
        optstore.add_project_option(OptionKey(name, 'sub'), vo2)
        self.assertEqual(optstore.get_value_for(name, ''), top_value)
        self.assertEqual(optstore.get_value_for(name, 'sub'), sub_value)
        self.assertEqual(num_options(optstore), 2)

    def test_toplevel_project_yielding(self):
        optstore = OptionStore(False)
        name = 'someoption'
        top_value = 'top'
        vo = UserStringOption(name, 'A top level option', top_value, True)
        optstore.add_project_option(OptionKey(name, ''), vo)
        self.assertEqual(optstore.get_value_for(name, ''), top_value)

    def test_project_yielding(self):
        optstore = OptionStore(False)
        name = 'someoption'
        top_value = 'top'
        sub_value = 'sub'
        vo = UserStringOption(name, 'A top level option', top_value)
        optstore.add_project_option(OptionKey(name, ''), vo)
        self.assertEqual(optstore.get_value_for(name, ''), top_value)
        self.assertEqual(num_options(optstore), 1)
        vo2 = UserStringOption(name, 'A subproject option', sub_value, True)
        optstore.add_project_option(OptionKey(name, 'sub'), vo2)
        self.assertEqual(optstore.get_value_for(name, ''), top_value)
        self.assertEqual(optstore.get_value_for(name, 'sub'), top_value)
        self.assertEqual(num_options(optstore), 2)

    def test_project_yielding_not_defined_in_top_project(self):
        optstore = OptionStore(False)
        top_name = 'a_name'
        top_value = 'top'
        sub_name = 'different_name'
        sub_value = 'sub'
        vo = UserStringOption(top_name, 'A top level option', top_value)
        optstore.add_project_option(OptionKey(top_name, ''), vo)
        self.assertEqual(optstore.get_value_for(top_name, ''), top_value)
        self.assertEqual(num_options(optstore), 1)
        vo2 = UserStringOption(sub_name, 'A subproject option', sub_value, True)
        optstore.add_project_option(OptionKey(sub_name, 'sub'), vo2)
        self.assertEqual(optstore.get_value_for(top_name, ''), top_value)
        self.assertEqual(optstore.get_value_for(sub_name, 'sub'), sub_value)
        self.assertEqual(num_options(optstore), 2)

    def test_project_yielding_initialize(self):
        optstore = OptionStore(False)
        name = 'someoption'
        top_value = 'top'
        sub_value = 'sub'
        subp = 'subp'
        cmd_line = { OptionKey(name): top_value, OptionKey(name, subp): sub_value }

        vo = UserStringOption(name, 'A top level option', 'default1')
        optstore.add_project_option(OptionKey(name, ''), vo)
        optstore.initialize_from_top_level_project_call({}, cmd_line, {})
        self.assertEqual(optstore.get_value_for(name, ''), top_value)
        self.assertEqual(num_options(optstore), 1)

        vo2 = UserStringOption(name, 'A subproject option', 'default2', True)
        optstore.add_project_option(OptionKey(name, 'subp'), vo2)
        self.assertEqual(optstore.get_value_for(name, ''), top_value)
        self.assertEqual(optstore.get_value_for(name, subp), top_value)
        self.assertEqual(num_options(optstore), 2)

        optstore.initialize_from_subproject_call(subp, {}, {}, cmd_line, {})
        self.assertEqual(optstore.get_value_for(name, ''), top_value)
        self.assertEqual(optstore.get_value_for(name, subp), sub_value)

    def test_augments(self):
        optstore = OptionStore(False)
        name = 'cpp_std'
        sub_name = 'sub'
        sub2_name = 'sub2'
        top_value = 'c++11'
        aug_value = 'c++23'

        co = UserComboOption(name,
                             'C++ language standard to use',
                             top_value,
                             choices=['c++98', 'c++11', 'c++14', 'c++17', 'c++20', 'c++23'])
        optstore.add_system_option(name, co)
        self.assertEqual(optstore.get_value_for(name), top_value)
        self.assertEqual(optstore.get_value_for(name, sub_name), top_value)
        self.assertEqual(optstore.get_value_for(name, sub2_name), top_value)

        # First augment a subproject
        with self.subTest('set subproject override'):
            optstore.set_from_configure_command({OptionKey.from_string(f'{sub_name}:{name}'): aug_value})
            self.assertEqual(optstore.get_value_for(name), top_value)
            self.assertEqual(optstore.get_value_for(name, sub_name), aug_value)
            self.assertEqual(optstore.get_value_for(name, sub2_name), top_value)

        with self.subTest('unset subproject override'):
            optstore.set_from_configure_command({OptionKey.from_string(f'{sub_name}:{name}'): None})
            self.assertEqual(optstore.get_value_for(name), top_value)
            self.assertEqual(optstore.get_value_for(name, sub_name), top_value)
            self.assertEqual(optstore.get_value_for(name, sub2_name), top_value)

        # And now augment the top level option
        optstore.set_from_configure_command({OptionKey.from_string(f':{name}'): aug_value})
        self.assertEqual(optstore.get_value_for(name, None), top_value)
        self.assertEqual(optstore.get_value_for(name, ''), aug_value)
        self.assertEqual(optstore.get_value_for(name, sub_name), top_value)
        self.assertEqual(optstore.get_value_for(name, sub2_name), top_value)

        optstore.set_from_configure_command({OptionKey.from_string(f':{name}'): None})
        self.assertEqual(optstore.get_value_for(name), top_value)
        self.assertEqual(optstore.get_value_for(name, sub_name), top_value)
        self.assertEqual(optstore.get_value_for(name, sub2_name), top_value)

    def test_augment_set_sub(self):
        optstore = OptionStore(False)
        name = 'cpp_std'
        sub_name = 'sub'
        sub2_name = 'sub2'
        top_value = 'c++11'
        aug_value = 'c++23'
        set_value = 'c++20'

        co = UserComboOption(name,
                             'C++ language standard to use',
                             top_value,
                             choices=['c++98', 'c++11', 'c++14', 'c++17', 'c++20', 'c++23'],
                             )
        optstore.add_system_option(name, co)
        optstore.set_from_configure_command({OptionKey.from_string(f'{sub_name}:{name}'): aug_value})
        optstore.set_from_configure_command({OptionKey.from_string(f'{sub_name}:{name}'): set_value})
        self.assertEqual(optstore.get_value_for(name), top_value)
        self.assertEqual(optstore.get_value_for(name, sub_name), set_value)

    def test_build_to_host(self):
        key = OptionKey('cpp_std')
        def_value = 'c++98'
        opt_value = 'c++17'
        optstore = OptionStore(False)
        co = UserComboOption(key.name,
                             'C++ language standard to use',
                             def_value,
                             choices=['c++98', 'c++11', 'c++14', 'c++17', 'c++20', 'c++23'],
                             )
        optstore.add_compiler_option('cpp', key, co)

        cmd_line = {key: opt_value}
        optstore.initialize_from_top_level_project_call({}, cmd_line, {})
        self.assertEqual(optstore.get_option_and_value_for(key.as_build())[1], opt_value)
        self.assertEqual(optstore.get_value_for(key.as_build()), opt_value)

    def test_build_to_host_subproject(self):
        key = OptionKey('cpp_std')
        def_value = 'c++98'
        opt_value = 'c++17'
        subp = 'subp'
        optstore = OptionStore(False)
        co = UserComboOption(key.name,
                             'C++ language standard to use',
                             def_value,
                             choices=['c++98', 'c++11', 'c++14', 'c++17', 'c++20', 'c++23'],
                             )
        optstore.add_compiler_option('cpp', key, co)

        spcall = {key: opt_value}
        optstore.initialize_from_top_level_project_call({}, {}, {})
        optstore.initialize_from_subproject_call(subp, spcall, {}, {}, {})
        self.assertEqual(optstore.get_option_and_value_for(key.evolve(subproject=subp,
                                                                            machine=MachineChoice.BUILD))[1], opt_value)
        self.assertEqual(optstore.get_value_for(key.evolve(subproject=subp,
                                                           machine=MachineChoice.BUILD)), opt_value)

    def test_build_to_host_cross(self):
        key = OptionKey('cpp_std')
        def_value = 'c++98'
        opt_value = 'c++17'
        optstore = OptionStore(True)
        for k in [key, key.as_build()]:
            co = UserComboOption(key.name,
                                 'C++ language standard to use',
                                 def_value,
                                 choices=['c++98', 'c++11', 'c++14', 'c++17', 'c++20', 'c++23'],
                                 )
            optstore.add_compiler_option('cpp', k, co)

        cmd_line = {key: opt_value}
        optstore.initialize_from_top_level_project_call({}, cmd_line, {})
        print(optstore.options)

        self.assertEqual(optstore.get_option_and_value_for(key)[1], opt_value)
        self.assertEqual(optstore.get_option_and_value_for(key.as_build())[1], def_value)
        self.assertEqual(optstore.get_value_for(key), opt_value)
        self.assertEqual(optstore.get_value_for(key.as_build()), def_value)

    def test_b_nonexistent(self):
        optstore = OptionStore(False)
        self.assertTrue(optstore.accept_as_pending_option(OptionKey('b_ndebug')))
        self.assertFalse(optstore.accept_as_pending_option(OptionKey('b_whatever')))

    def test_backend_option_pending(self):
        optstore = OptionStore(False)
        # backend options are known after the first invocation
        self.assertTrue(optstore.accept_as_pending_option(OptionKey('backend_whatever'), True))
        self.assertFalse(optstore.accept_as_pending_option(OptionKey('backend_whatever'), False))

    def test_reconfigure_b_nonexistent(self):
        optstore = OptionStore(False)
        optstore.set_from_configure_command({OptionKey('b_ndebug'): True})

    def test_unconfigure_nonexistent(self):
        optstore = OptionStore(False)
        with self.assertRaises(MesonException):
            optstore.set_from_configure_command({OptionKey('nonexistent'): None})

    def test_subproject_proj_opt_with_same_name(self):
        name = 'tests'
        subp = 'subp'

        optstore = OptionStore(False)
        prefix = UserStringOption('prefix', 'This is needed by OptionStore', '/usr')
        optstore.add_system_option('prefix', prefix)
        o = UserBooleanOption(name, 'Tests', False)
        optstore.add_project_option(OptionKey(name, subproject=''), o)
        o = UserBooleanOption(name, 'Tests', True)
        optstore.add_project_option(OptionKey(name, subproject=subp), o)

        cmd_line = {OptionKey(name): True}
        spcall = {OptionKey(name): False}

        optstore.initialize_from_top_level_project_call({}, cmd_line, {})
        optstore.initialize_from_subproject_call(subp, spcall, {}, cmd_line, {})
        self.assertEqual(optstore.get_value_for(name, ''), True)
        self.assertEqual(optstore.get_value_for(name, subp), False)

    def test_subproject_cmdline_override_global(self):
        name = 'optimization'
        subp = 'subp'
        new_value = '0'

        optstore = OptionStore(False)
        prefix = UserStringOption('prefix', 'This is needed by OptionStore', '/usr')
        optstore.add_system_option('prefix', prefix)
        o = UserComboOption(name, 'Optimization level', '0', choices=['plain', '0', 'g', '1', '2', '3', 's'])
        optstore.add_system_option(name, o)

        toplevel_proj_default = {OptionKey(name): 's'}
        subp_proj_default = {OptionKey(name): '3'}
        cmd_line = {OptionKey(name): new_value}

        optstore.initialize_from_top_level_project_call(toplevel_proj_default, cmd_line, {})
        optstore.initialize_from_subproject_call(subp, {}, subp_proj_default, cmd_line, {})
        self.assertEqual(optstore.get_value_for(name, subp), new_value)
        self.assertEqual(optstore.get_value_for(name), new_value)

    def test_subproject_parent_override_subp(self):
        name = 'optimization'
        subp = 'subp'
        default_value = 's'
        subp_value = '0'

        optstore = OptionStore(False)
        prefix = UserStringOption('prefix', 'This is needed by OptionStore', '/usr')
        optstore.add_system_option('prefix', prefix)
        o = UserComboOption(name, 'Optimization level', '0', choices=['plain', '0', 'g', '1', '2', '3', 's'])
        optstore.add_system_option(name, o)

        toplevel_proj_default = {OptionKey(name, subproject=subp): subp_value, OptionKey(name): default_value}
        subp_proj_default = {OptionKey(name): '3'}

        optstore.initialize_from_top_level_project_call(toplevel_proj_default, {}, {})
        optstore.initialize_from_subproject_call(subp, {}, subp_proj_default, {}, {})
        self.assertEqual(optstore.get_value_for(name, subp), subp_value)
        self.assertEqual(optstore.get_value_for(name), default_value)

    def test_subproject_cmdline_override_global_and_augment(self):
        name = 'optimization'
        subp = 'subp'
        global_value = 's'
        new_value = '0'

        optstore = OptionStore(False)
        prefix = UserStringOption('prefix', 'This is needed by OptionStore', '/usr')
        optstore.add_system_option('prefix', prefix)
        o = UserComboOption(name, 'Optimization level', '0', choices=['plain', '0', 'g', '1', '2', '3', 's'])
        optstore.add_system_option(name, o)

        toplevel_proj_default = {OptionKey(name): '1'}
        subp_proj_default = {OptionKey(name): '3'}
        cmd_line = {OptionKey(name): global_value, OptionKey(name, subproject=subp): new_value}

        optstore.initialize_from_top_level_project_call(toplevel_proj_default, cmd_line, {})
        optstore.initialize_from_subproject_call(subp, {}, subp_proj_default, cmd_line, {})
        self.assertEqual(optstore.get_value_for(name, subp), new_value)
        self.assertEqual(optstore.get_value_for(name), global_value)

    def test_subproject_cmdline_override_toplevel(self):
        name = 'default_library'
        subp = 'subp'
        toplevel_value = 'both'
        subp_value = 'static'

        optstore = OptionStore(False)
        prefix = UserStringOption('prefix', 'This is needed by OptionStore', '/usr')
        optstore.add_system_option('prefix', prefix)
        o = UserComboOption(name, 'Kind of library', 'both', choices=['shared', 'static', 'both'])
        optstore.add_system_option(name, o)

        toplevel_proj_default = {OptionKey(name): 'shared'}
        subp_proj_default = {OptionKey(name): subp_value}
        cmd_line = {OptionKey(name, subproject=''): toplevel_value}

        optstore.initialize_from_top_level_project_call(toplevel_proj_default, cmd_line, {})
        optstore.initialize_from_subproject_call(subp, {}, subp_proj_default, cmd_line, {})
        self.assertEqual(optstore.get_value_for(name, subp), subp_value)
        self.assertEqual(optstore.get_value_for(name, ''), toplevel_value)

    def test_subproject_buildtype(self):
        subp = 'subp'
        main1 = {OptionKey('buildtype'): 'release'}
        main2 = {OptionKey('optimization'): '3', OptionKey('debug'): 'false'}
        sub1 = {OptionKey('buildtype'): 'debug'}
        sub2 = {OptionKey('optimization'): '0', OptionKey('debug'): 'true'}

        for mainopt, subopt in ((main1, sub1),
                          (main2, sub2),
                          ({**main1, **main2}, {**sub1, **sub2})):
            optstore = OptionStore(False)
            prefix = UserStringOption('prefix', 'This is needed by OptionStore', '/usr')
            optstore.add_system_option('prefix', prefix)
            o = UserComboOption('buildtype', 'Build type to use', 'debug', choices=['plain', 'debug', 'debugoptimized', 'release', 'minsize', 'custom'])
            optstore.add_system_option(o.name, o)
            o = UserComboOption('optimization', 'Optimization level', '0', choices=['plain', '0', 'g', '1', '2', '3', 's'])
            optstore.add_system_option(o.name, o)
            o = UserBooleanOption('debug', 'Enable debug symbols and other information', True)
            optstore.add_system_option(o.name, o)

            optstore.initialize_from_top_level_project_call(mainopt, {}, {})
            optstore.initialize_from_subproject_call(subp, {}, subopt, {}, {})
            self.assertEqual(optstore.get_value_for('buildtype', subp), 'debug')
            self.assertEqual(optstore.get_value_for('optimization', subp), '0')
            self.assertEqual(optstore.get_value_for('debug', subp), True)

    def test_deprecated_nonstring_value(self):
        # TODO: add a lot more deprecated option tests
        optstore = OptionStore(False)
        name = 'deprecated'
        do = UserStringOption(name, 'An option with some deprecation', '0',
                              deprecated={'true': '1'})
        optstore.add_system_option(name, do)
        optstore.set_option(OptionKey(name), True)
        value = optstore.get_value_for(name)
        self.assertEqual(value, '1')

    def test_pending_augment_validation(self):
        name = 'b_lto'
        subproject = 'mysubproject'

        optstore = OptionStore(False)
        prefix = UserStringOption('prefix', 'This is needed by OptionStore', '/usr')
        optstore.add_system_option('prefix', prefix)

        optstore.initialize_from_top_level_project_call({}, {}, {})
        optstore.initialize_from_subproject_call(subproject, {}, {OptionKey(name): 'true'}, {}, {})

        bo = UserBooleanOption(name, 'LTO', False)
        key = OptionKey(name, subproject=subproject)
        optstore.add_system_option(key, bo)
        stored_value = optstore.get_value_for(key)
        self.assertIsInstance(stored_value, bool)
        self.assertTrue(stored_value)

    def test_yielding_boolean_option_with_falsy_parent(self):
        """Test that yielding is correctly initialized when parent option value is False."""
        optstore = OptionStore(False)
        name = 'someoption'
        subproject_name = 'sub'
        parent_option = UserBooleanOption(name, 'A parent boolean option', False, yielding=True)
        optstore.add_project_option(OptionKey(name, ''), parent_option)

        child_option = UserBooleanOption(name, 'A child boolean option', True, yielding=True)
        child_key = OptionKey(name, subproject_name)
        optstore.add_project_option(child_key, child_option)
        self.assertTrue(optstore.options[child_key].yielding)

    def test_machine_canonicalization_cross(self):
        """Test that BUILD machine options are handled correctly in cross compilation."""
        optstore = OptionStore(True)

        # Test that BUILD machine per-machine option is NOT canonicalized to HOST
        host_pkg_config = OptionKey('pkg_config_path', machine=MachineChoice.HOST)
        build_pkg_config = OptionKey('pkg_config_path', machine=MachineChoice.BUILD)
        host_option_obj = UserStringArrayOption('pkg_config_path', 'Host pkg-config paths', ['/mingw/lib64/pkgconfig'])
        build_option_obj = UserStringArrayOption('pkg_config_path', 'Build pkg-config paths', ['/usr/lib64/pkgconfig'])
        optstore.add_system_option(host_pkg_config, host_option_obj)
        optstore.add_system_option(build_pkg_config, build_option_obj)
        option, value = optstore.get_option_and_value_for(build_pkg_config)
        self.assertEqual(value, ['/usr/lib64/pkgconfig'])

        # Test that non-per-machine BUILD option IS canonicalized to HOST
        build_opt = OptionKey('optimization', machine=MachineChoice.BUILD)
        host_opt = OptionKey('optimization', machine=MachineChoice.HOST)
        common_option_obj = UserComboOption('optimization', 'Optimization level', '0',
                                            choices=['plain', '0', 'g', '1', '2', '3', 's'])
        optstore.add_system_option(host_opt, common_option_obj)
        self.assertEqual(optstore.get_value_for(build_opt), '0')

    def test_machine_canonicalization_native(self):
        """Test that BUILD machine options are canonicalized to HOST when not cross compiling."""
        optstore = OptionStore(False)

        host_pkg_config = OptionKey('pkg_config_path', machine=MachineChoice.HOST)
        build_pkg_config = OptionKey('pkg_config_path', machine=MachineChoice.BUILD)
        host_option_obj = UserStringArrayOption('pkg_config_path', 'Host pkg-config paths', ['/mingw/lib64/pkgconfig'])
        build_option_obj = UserStringArrayOption('pkg_config_path', 'Build pkg-config paths', ['/usr/lib64/pkgconfig'])

        # Add per-machine option for HOST only (BUILD will be canonicalized)
        optstore.add_system_option(host_pkg_config, host_option_obj)
        option, value = optstore.get_option_and_value_for(build_pkg_config)
        self.assertEqual(value, ['/mingw/lib64/pkgconfig'])

        # Try again adding build option too, for completeness
        optstore.add_system_option(build_pkg_config, build_option_obj)
        option, value = optstore.get_option_and_value_for(build_pkg_config)
        self.assertEqual(value, ['/mingw/lib64/pkgconfig'])

    def test_sanitize_prefix_windows_host(self):
        """Test that Windows paths are accepted when host is Windows."""
        optstore = OptionStore(True)  # cross-compile
        optstore.set_host_machine(make_machine('windows'))
        result = optstore.sanitize_prefix('C:\\Windows')
        self.assertEqual(result, 'C:\\Windows')
        result = optstore.sanitize_prefix('\\\\server\\share')
        self.assertEqual(result, '\\\\server\\share')
        # Forward slashes should also be accepted on Windows
        result = optstore.sanitize_prefix('C:/Windows')
        self.assertEqual(result, 'C:/Windows')
        result = optstore.sanitize_prefix('//server/share')
        self.assertEqual(result, '//server/share')

    def test_sanitize_prefix_posix_host(self):
        """Test that POSIX paths are accepted when host is POSIX."""
        optstore = OptionStore(True)  # cross-compile
        optstore.set_host_machine(make_machine('linux'))
        result = optstore.sanitize_prefix('/usr/local')
        self.assertEqual(result, '/usr/local')
        # Windows path should be rejected
        with self.assertRaises(MesonException):
            optstore.sanitize_prefix('\\myprog')
        with self.assertRaises(MesonException):
            optstore.sanitize_prefix('C:\\Windows')
        with self.assertRaises(MesonException):
            optstore.sanitize_prefix('C:/Windows')
        with self.assertRaises(MesonException):
            optstore.sanitize_prefix('\\\\server\\share')
        # This one is not parsed as UNC
        result = optstore.sanitize_prefix('//server/share')
        self.assertEqual(result, '//server/share')

    def test_sanitize_prefix_cygwin_host(self):
        """Test that Cygwin uses POSIX-style paths."""
        optstore = OptionStore(True)
        optstore.set_host_machine(make_machine('cygwin'))
        result = optstore.sanitize_prefix('/usr/local')
        self.assertEqual(result, '/usr/local')
        result = optstore.sanitize_prefix('/cygdrive/c/Windows')
        self.assertEqual(result, '/cygdrive/c/Windows')

    def test_sanitize_dir_option_cross_to_windows(self):
        """Test directory option sanitization when cross-compiling to Windows."""
        optstore = OptionStore(True)
        optstore.set_host_machine(make_machine('windows'))
        optstore.init_builtins()
        # Set libdir to absolute path inside prefix, should be relativized
        optstore.set_option(OptionKey('prefix'), 'C:\\Program Files\\MyProg')
        optstore.set_option(OptionKey('libdir'), 'C:\\Program Files\\MyProg\\lib')
        self.assertEqual(optstore.get_value_for('libdir'), 'lib')

    def test_sanitize_dir_option_cross_to_linux(self):
        """Test directory option sanitization when cross-compiling to Linux."""
        optstore = OptionStore(True)
        optstore.set_host_machine(make_machine('linux'))
        optstore.init_builtins()
        # Set libdir to absolute path inside prefix, should be relativized
        optstore.set_option(OptionKey('prefix'), '/opt/myapp')
        optstore.set_option(OptionKey('libdir'), '/opt/myapp/lib64')
        self.assertEqual(optstore.get_value_for('libdir'), 'lib64')

    def test_sanitize_prefix_native_path(self):
        """Test that native paths are accepted without set_host_machine()."""
        optstore = OptionStore(False)
        native_path = os.sep + 'myprog'
        result = optstore.sanitize_prefix(native_path)
        self.assertEqual(result, native_path)

    def test_is_host_absolute(self):
        """Test _is_host_absolute with various host configurations."""
        # POSIX host
        optstore = OptionStore(True)
        optstore.set_host_machine(make_machine('linux'))
        self.assertTrue(optstore._is_host_absolute('/usr'))
        self.assertTrue(optstore._is_host_absolute('/usr/local'))
        self.assertFalse(optstore._is_host_absolute('relative'))
        self.assertFalse(optstore._is_host_absolute('C:\\Windows'))
        self.assertFalse(optstore._is_host_absolute('C:/Windows'))

        # Windows host - accepts both full absolute and root-relative
        optstore = OptionStore(True)
        optstore.set_host_machine(make_machine('windows'))
        self.assertTrue(optstore._is_host_absolute('C:\\Windows'))
        self.assertTrue(optstore._is_host_absolute('C:/Windows'))
        self.assertTrue(optstore._is_host_absolute('//server/share'))
        self.assertTrue(optstore._is_host_absolute('\\\\server\\share'))
        # Root-relative paths accepted for backwards compat
        self.assertTrue(optstore._is_host_absolute('/usr'))
        self.assertTrue(optstore._is_host_absolute('\\myprog'))
        self.assertFalse(optstore._is_host_absolute('relative'))

        # No host set - uses build machine semantics
        optstore = OptionStore(False)
        self.assertTrue(optstore._is_host_absolute(os.sep + 'myprog'))
        self.assertTrue(optstore._is_host_absolute('/myprog'))
