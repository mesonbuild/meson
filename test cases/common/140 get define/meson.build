project('get define', 'c', 'cpp')

host_system = host_machine.system()

foreach lang : ['c', 'cpp']
  cc = meson.get_compiler(lang)
  if host_system == 'linux'
    d = cc.get_define('__linux__')
    assert(d == '1', '__linux__ value is @0@ instead of 1'.format(d))
  elif host_system == 'darwin'
    d = cc.get_define('__APPLE__')
    assert(d == '1', '__APPLE__ value is @0@ instead of 1'.format(d))
  elif host_system == 'windows'
    d = cc.get_define('_WIN32')
    assert(d == '1', '_WIN32 value is @0@ instead of 1'.format(d))
  elif host_system == 'cygwin'
    d = cc.get_define('__CYGWIN__')
    assert(d == '1', '__CYGWIN__ value is @0@ instead of 1'.format(d))
  else
    error('Please report a bug and help us improve support for this platform')
  endif

  # Check that an undefined value is empty.
  have = cc.get_define('MESON_FAIL_VALUE')
  assert(have == '', 'MESON_FAIL_VALUE value is "@0@" instead of ""'.format(have))

  # This is used in the test_preprocessor_checks_CPPFLAGS() unit test.
  have = cc.get_define('MESON_TEST_DEFINE_VALUE')
  expect = get_option('MESON_TEST_DEFINE_VALUE')
  assert(have == expect, 'MESON_TEST_DEFINE_VALUE value is "@0@" instead of "@1@"'.format(have, expect))
endforeach
