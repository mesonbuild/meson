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
  elif host_system == 'haiku'
    d = cc.get_define('__HAIKU__')
    assert(d == '1', '__HAIKU__ value is @0@ instead of 1'.format(d))
  elif host_system == 'freebsd'
    # the __FreeBSD__ define will be equal to the major version of the release
    # (ex, in FreeBSD 11.x, __FreeBSD__ == 11). To make the test robust when
    # being run on various versions of FreeBSD, just test that the define is
    # set.
    d = cc.get_define('__FreeBSD__')
    assert(d != '', '__FreeBSD__ value is unset')
  elif host_system == 'dragonfly'
    d = cc.get_define('__DragonFly__')
    assert(d == '1', '__DragonFly__ value is @0@ instead of 1'.format(d))
  elif host_system == 'netbsd'
    d = cc.get_define('__NetBSD__')
    assert(d == '1', '__NetBSD__ value is @0@ instead of 1'.format(d))
  elif host_system == 'openbsd'
    d = cc.get_define('__OpenBSD__')
    assert(d == '1', '__OpenBSD__ value is @0@ instead of 1'.format(d))
  elif host_system == 'gnu'
    d = cc.get_define('__GNU__')
    assert(d == '1', '__GNU__ value is @0@ instead of 1'.format(d))
  elif host_system == 'sunos'
    d = cc.get_define('__sun__')
    assert(d == '1', '__sun__ value is @0@ instead of 1'.format(d))
  else
    error('Please report a bug and help us improve support for this platform')
  endif

  if cc.find_library('z', required : false).found()
    # When a C file containing #include <foo.h> is pre-processed and foo.h is
    # found in the compiler's default search path, GCC inserts an extra comment
    # between the delimiter and the define which causes a parsing error.
    # https://github.com/mesonbuild/meson/issues/1726
    if host_machine.system() == 'netbsd' or host_machine.system() == 'openbsd'
      # NetBSD and OpenBSD's zlib don't have a ZLIB_VER_MAJOR, but they do have
      # a ZLIB_VERSION (which is a string), so check the first non-quote
      # character of that.
      ver = cc.get_define('ZLIB_VERSION', prefix : '#include <zlib.h>')[1]
      assert(ver == '1', 'ZLIB_VERSION (major) value is "@0@" instead of "1"'.format(ver))
    else
      ver = cc.get_define('ZLIB_VER_MAJOR', prefix : '#include <zlib.h>')
      assert(ver == '1', 'ZLIB_VER_MAJOR value is "@0@" instead of "1"'.format(ver))
    endif
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
    lang_arg = meson.get_cross_property(lang + '_args', '')
    if lang_arg == '-DMESON_TEST_ISSUE_1665=1'
      run_1665_test = true
    endif
  endif

  if run_1665_test
    have = cc.get_define('MESON_TEST_ISSUE_1665')
    assert(have == '1', 'MESON_TEST_ISSUE_1665 value is "@0@" instead of "1"'.format(have))
  endif

  have = cc.get_define('TEST_VERSION_STR',
        prefix : '#include <concat.h>', include_directories: include_directories('.'))
  assert(have == '"6.0.0"', 'TEST_VERSION_STR value is "@0@" instead of ""6.0.0""'.format(have))

  concat_examples = {
  'TEST_CONCAT_1': '"abcdef"',
  'TEST_CONCAT_2': '1',
  'TEST_CONCAT_3': '1 2 3',
  'TEST_CONCAT_4': '"ab" 1 "cd"',
  'TEST_CONCAT_5': '"ab\"cd"',
  'TEST_CONCAT_6': '"ab\" \"cd"',
  }
  foreach def,expected : concat_examples
    have = cc.get_define(def,
          prefix : '#include <concat.h>', include_directories: include_directories('.'))
    assert(have == expected, '@0@ value is "@1@" instead of "@2@"'.format(def, have, expected))
  endforeach
endforeach
