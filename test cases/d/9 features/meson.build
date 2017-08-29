project('D Features', 'd')
dc = meson.get_compiler('d')

# directory for data
data_dir = join_paths(meson.current_source_dir(), 'data')

# test string import dirs only
dfeatures_simple = dc.feature_args(import_dirs: [data_dir])

e_plain = executable('dapp_menu', 'app.d', d_args: dfeatures_simple)
test('dapp_menu_t_fail', e_plain, should_fail: true)
test('dapp_menu_t', e_plain, args: ['menu'])

# test feature versions and string imports
dfeatures_version = dc.feature_args(import_dirs: [data_dir], versions: ['No_Menu', 'With_People'])
e_versions = executable('dapp_versions', 'app.d', d_args: dfeatures_version)
test('dapp_versions_t_fail', e_versions, args: ['menu'], should_fail: true)
test('dapp_versions_t', e_versions, args: ['people'])

# test everything and unittests
dfeatures_test = dc.feature_args(
    import_dirs: [data_dir],
    versions: ['No_Menu', 'With_People'],
    unittest: true
)
e_test = executable('dapp_test', 'app.d',
    d_args: dfeatures_test)
test('dapp_test', e_test)
