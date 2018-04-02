project('D Features', 'd')

# ONLY FOR BACKWARDS COMPATIBILITY.
# DO NOT DO THIS IN NEW CODE!
# USE include_directories() INSTEAD OF BUILDING
# STRINGS TO PATHS MANUALLY!
data_dir = join_paths(meson.current_source_dir(), 'data')

test_src = ['app.d', 'extra.d']

e_plain_bcompat = executable('dapp_menu_bcompat',
    test_src,
    d_import_dirs: [data_dir]
)
test('dapp_menu_t_fail_bcompat', e_plain_bcompat, should_fail: true)
test('dapp_menu_t_bcompat', e_plain_bcompat, args: ['menu'])

# directory for data
# This is the correct way to do this.
data_dir = include_directories('data')

e_plain = executable('dapp_menu',
    test_src,
    d_import_dirs: [data_dir]
)
test('dapp_menu_t_fail', e_plain, should_fail: true)
test('dapp_menu_t', e_plain, args: ['menu'])


# test feature versions and string imports
e_versions = executable('dapp_versions',
    test_src,
    d_import_dirs: [data_dir],
    d_module_versions: ['No_Menu', 'With_People']
)
test('dapp_versions_t_fail', e_versions, args: ['menu'], should_fail: true)
test('dapp_versions_t', e_versions, args: ['people'])

# test everything and unittests
e_test = executable('dapp_test',
    test_src,
    d_import_dirs: [data_dir],
    d_module_versions: ['No_Menu', 'With_People'],
    d_unittest: true
)
test('dapp_test', e_test)
