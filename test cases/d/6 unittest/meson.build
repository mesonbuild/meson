project('D Unittests', 'd')

e = executable('dapp', 'app.d', install : true)
test('dapp_run', e, should_fail: true)

e_test = executable('dapp_test', 'app.d',
    d_args: meson.get_compiler('d').unittest_args())
test('dapp_test', e_test)
