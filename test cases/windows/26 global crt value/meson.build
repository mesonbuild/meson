project('global-crt-value', 'c')

if host_machine.system() != 'windows'
  error('MESON_SKIP_TEST: unsupported platform')
endif

c = meson.get_compiler('c')
if c.get_argument_syntax() != 'msvc'
  error('MESON_SKIP_TEST: unsupported compiler')
endif

liba_dep = subproject('liba').get_variable('liba_dep')

test_exe = executable('test-same-crt',
                      sources: ['test.c'],
                      dependencies: [liba_dep])

test('test-same-crt', test_exe)
