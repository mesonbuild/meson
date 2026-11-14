project(
    'native command sequence',
    'c',
    default_options: ['buildtype=release'],
)

if host_machine.system() == 'windows'
  error('MESON_SKIP_TEST: /usr/bin/env is not available on Windows')
endif

py = import('python').find_installation(pure: false)

ct = custom_target(
  'ct',
  input : 'gen.py',
  output : 'ct.c',
  command : [py, '@INPUT@', '@OUTPUT@'],
)

exe = executable('test_generated_code', ct, 'test_generated_code.c')

test('runtest', exe)
