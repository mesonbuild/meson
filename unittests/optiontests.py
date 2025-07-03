# SPDX-License-Identifier: Apache-2.0
# Copyright 2024 Meson project contributors

from mesonbuild.options import *

import unittest


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
        self.assertEqual(optstore.get_value_for_unsafe(name), default_value)
        optstore.set_option(OptionKey.from_string(name), new_value)
        self.assertEqual(optstore.get_value_for_unsafe(name), new_value)

    def test_toplevel_project(self):
        optstore = OptionStore(False)
        name = 'someoption'
        default_value = 'somevalue'
        new_value = 'new_value'
        k = OptionKey(name)
        vo = UserStringOption(k.name, 'An option of some sort', default_value)
        optstore.add_system_option(k.name, vo)
        self.assertEqual(optstore.get_value_for_unsafe(k), default_value)
        optstore.initialize_from_top_level_project_call({OptionKey('someoption'): new_value}, {}, {})
        self.assertEqual(optstore.get_value_for_unsafe(k), new_value)

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
        self.assertEqual(optstore.get_value_for_unsafe(k), default_value)
        optstore.initialize_from_top_level_project_call({OptionKey(name): proj_value}, {},
                                                        {OptionKey(name): mfile_value})
        self.assertEqual(optstore.get_value_for_unsafe(k), mfile_value)

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
        self.assertEqual(optstore.get_value_for_unsafe(subk), new_value)

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
        self.assertEqual(optstore.get_value_for_unsafe(name, 'somesubproject'), default_value)

    def test_reset(self):
        optstore = OptionStore(False)
        name = 'someoption'
        original_value = 'original'
        reset_value = 'reset'
        vo = UserStringOption(name, 'An option set twice', original_value)
        optstore.add_system_option(name, vo)
        self.assertEqual(optstore.get_value_for_unsafe(name), original_value)
        self.assertEqual(num_options(optstore), 1)
        vo2 = UserStringOption(name, 'An option set twice', reset_value)
        optstore.add_system_option(name, vo2)
        self.assertEqual(optstore.get_value_for_unsafe(name), original_value)
        self.assertEqual(num_options(optstore), 1)

    def test_project_nonyielding(self):
        optstore = OptionStore(False)
        name = 'someoption'
        top_value = 'top'
        sub_value = 'sub'
        vo = UserStringOption(name, 'A top level option', top_value, False)
        optstore.add_project_option(OptionKey(name, ''), vo)
        self.assertEqual(optstore.get_value_for_unsafe(name, ''), top_value, False)
        self.assertEqual(num_options(optstore), 1)
        vo2 = UserStringOption(name, 'A subproject option', sub_value)
        optstore.add_project_option(OptionKey(name, 'sub'), vo2)
        self.assertEqual(optstore.get_value_for_unsafe(name, ''), top_value)
        self.assertEqual(optstore.get_value_for_unsafe(name, 'sub'), sub_value)
        self.assertEqual(num_options(optstore), 2)

    def test_project_yielding(self):
        optstore = OptionStore(False)
        name = 'someoption'
        top_value = 'top'
        sub_value = 'sub'
        vo = UserStringOption(name, 'A top level option', top_value)
        optstore.add_project_option(OptionKey(name, ''), vo)
        self.assertEqual(optstore.get_value_for_unsafe(name, ''), top_value)
        self.assertEqual(num_options(optstore), 1)
        vo2 = UserStringOption(name, 'A subproject option', sub_value, True)
        optstore.add_project_option(OptionKey(name, 'sub'), vo2)
        self.assertEqual(optstore.get_value_for_unsafe(name, ''), top_value)
        self.assertEqual(optstore.get_value_for_unsafe(name, 'sub'), top_value)
        self.assertEqual(num_options(optstore), 2)

    def test_project_yielding_not_defined_in_top_project(self):
        optstore = OptionStore(False)
        top_name = 'a_name'
        top_value = 'top'
        sub_name = 'different_name'
        sub_value = 'sub'
        vo = UserStringOption(top_name, 'A top level option', top_value)
        optstore.add_project_option(OptionKey(top_name, ''), vo)
        self.assertEqual(optstore.get_value_for_unsafe(top_name, ''), top_value)
        self.assertEqual(num_options(optstore), 1)
        vo2 = UserStringOption(sub_name, 'A subproject option', sub_value, True)
        optstore.add_project_option(OptionKey(sub_name, 'sub'), vo2)
        self.assertEqual(optstore.get_value_for_unsafe(top_name, ''), top_value)
        self.assertEqual(optstore.get_value_for_unsafe(sub_name, 'sub'), sub_value)
        self.assertEqual(num_options(optstore), 2)

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
        self.assertEqual(optstore.get_value_for_unsafe(name), top_value)
        self.assertEqual(optstore.get_value_for_unsafe(name, sub_name), top_value)
        self.assertEqual(optstore.get_value_for_unsafe(name, sub2_name), top_value)

        # First augment a subproject
        with self.subTest('set subproject override'):
            optstore.set_from_configure_command([f'{sub_name}:{name}={aug_value}'], [])
            self.assertEqual(optstore.get_value_for_unsafe(name), top_value)
            self.assertEqual(optstore.get_value_for_unsafe(name, sub_name), aug_value)
            self.assertEqual(optstore.get_value_for_unsafe(name, sub2_name), top_value)

        with self.subTest('unset subproject override'):
            optstore.set_from_configure_command([], [f'{sub_name}:{name}'])
            self.assertEqual(optstore.get_value_for_unsafe(name), top_value)
            self.assertEqual(optstore.get_value_for_unsafe(name, sub_name), top_value)
            self.assertEqual(optstore.get_value_for_unsafe(name, sub2_name), top_value)

        # And now augment the top level option
        optstore.set_from_configure_command([f':{name}={aug_value}'], [])
        self.assertEqual(optstore.get_value_for_unsafe(name, None), top_value)
        self.assertEqual(optstore.get_value_for_unsafe(name, ''), aug_value)
        self.assertEqual(optstore.get_value_for_unsafe(name, sub_name), top_value)
        self.assertEqual(optstore.get_value_for_unsafe(name, sub2_name), top_value)

        optstore.set_from_configure_command([], [f':{name}'])
        self.assertEqual(optstore.get_value_for_unsafe(name), top_value)
        self.assertEqual(optstore.get_value_for_unsafe(name, sub_name), top_value)
        self.assertEqual(optstore.get_value_for_unsafe(name, sub2_name), top_value)

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
        optstore.set_from_configure_command([f'{sub_name}:{name}={aug_value}'], [])
        optstore.set_from_configure_command([f'{sub_name}:{name}={set_value}'], [])
        self.assertEqual(optstore.get_value_for_unsafe(name), top_value)
        self.assertEqual(optstore.get_value_for_unsafe(name, sub_name), set_value)

    def test_b_default(self):
        optstore = OptionStore(False)
        value = optstore.get_default_for_b_option(OptionKey('b_vscrt'))
        self.assertEqual(value, 'from_buildtype')

    def test_b_nonexistent(self):
        optstore = OptionStore(False)
        self.assertTrue(optstore.accept_as_pending_option(OptionKey('b_ndebug')))
        self.assertFalse(optstore.accept_as_pending_option(OptionKey('b_whatever')))

    def test_backend_option_pending(self):
        optstore = OptionStore(False)
        # backend options are known after the first invocation
        self.assertTrue(optstore.accept_as_pending_option(OptionKey('backend_whatever'), set(), True))
        self.assertFalse(optstore.accept_as_pending_option(OptionKey('backend_whatever'), set(), False))

    def test_reconfigure_b_nonexistent(self):
        optstore = OptionStore(False)
        optstore.set_from_configure_command(['b_ndebug=true'], [])

    def test_subproject_nonexistent(self):
        optstore = OptionStore(False)
        subprojects = {'found'}
        self.assertFalse(optstore.accept_as_pending_option(OptionKey('foo', subproject='found'), subprojects))
        self.assertTrue(optstore.accept_as_pending_option(OptionKey('foo', subproject='whatisthis'), subprojects))

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
        self.assertEqual(optstore.get_value_for_unsafe(name, subp), new_value)
        self.assertEqual(optstore.get_value_for_unsafe(name), new_value)

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
        self.assertEqual(optstore.get_value_for_unsafe(name, subp), new_value)
        self.assertEqual(optstore.get_value_for_unsafe(name), global_value)

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
        self.assertEqual(optstore.get_value_for_unsafe(name, subp), subp_value)
        self.assertEqual(optstore.get_value_for_unsafe(name), toplevel_value)

    def test_deprecated_nonstring_value(self):
        # TODO: add a lot more deprecated option tests
        optstore = OptionStore(False)
        name = 'deprecated'
        do = UserStringOption(name, 'An option with some deprecation', '0',
                              deprecated={'true': '1'})
        optstore.add_system_option(name, do)
        optstore.set_option(OptionKey(name), True)
        value = optstore.get_value_for_unsafe(name)
        self.assertEqual(value, '1')
