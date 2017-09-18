project('D Features', 'd')

# directory for data
data_dir = join_paths(meson.current_source_dir(), 'data')

e_plain = executable('dapp_menu',
    'app.d',
    d_import_dirs: [data_dir]
)
test('dapp_menu_t_fail', e_plain, should_fail: true)
test('dapp_menu_t', e_plain, args: ['menu'])

# test feature versions and string imports
e_versions = executable('dapp_versions',
    'app.d',
    d_import_dirs: [data_dir],
    d_module_versions: ['No_Menu', 'With_People']
)
test('dapp_versions_t_fail', e_versions, args: ['menu'], should_fail: true)
test('dapp_versions_t', e_versions, args: ['people'])

# test everything and unittests
e_test = executable('dapp_test',
    'app.d',
    d_import_dirs: [data_dir],
    d_module_versions: ['No_Menu', 'With_People'],
    d_unittest: true
)
test('dapp_test', e_test)
