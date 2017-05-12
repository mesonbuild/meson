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

  if cc.find_library('z', required : false).found()
    # When a C file containing #include <foo.h> is pre-processed and foo.h is
    # found in the compiler's default search path, GCC inserts an extra comment
    # between the delimiter and the define which causes a parsing error.
    # https://github.com/mesonbuild/meson/issues/1726
    ver = cc.get_define('ZLIB_VER_MAJOR', prefix : '#include <zlib.h>')
    assert(ver == '1', 'ZLIB_VER_MAJOR value is "@0@" instead of "1"'.format(ver))
  endif

  # Check that an undefined value is empty.
  have = cc.get_define('MESON_FAIL_VALUE')
  assert(have == '', 'MESON_FAIL_VALUE value is "@0@" instead of ""'.format(have))

  # This is used in the test_preprocessor_checks_CPPFLAGS() unit test.
  have = cc.get_define('MESON_TEST_DEFINE_VALUE')
  expect = get_option('MESON_TEST_DEFINE_VALUE')
  assert(have == expect, 'MESON_TEST_DEFINE_VALUE value is "@0@" instead of "@1@"'.format(have, expect))

  run_1665_test = false
  if meson.is_cross_build()
    # Can't use an empty array as a fallback here because of
    # https://github.com/mesonbuild/meson/issues/1481
    lang_args = meson.get_cross_property(lang + '_args', false)
    if lang_args != false
      foreach lang_arg : lang_args
        if lang_arg.contains('MESON_TEST_ISSUE_1665')
          run_1665_test = true
        endif
      endforeach
    endif
  endif

  if run_1665_test
    have = cc.get_define('MESON_TEST_ISSUE_1665')
    assert(have == '1', 'MESON_TEST_ISSUE_1665 value is "@0@" instead of "1"'.format(have))
  endif
endforeach
