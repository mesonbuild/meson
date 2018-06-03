project('has function', 'c', 'cpp')

host_system = host_machine.system()

# This is used in the `test_compiler_check_flags_order` unit test
unit_test_args = '-I/tmp'
defines_has_builtin = '''#ifndef __has_builtin
#error "no __has_builtin"
#endif
'''
langs = ['c', 'cpp']

foreach lang : langs
  message('Running tests with @0@ compiler'.format(lang))
  cc = meson.get_compiler(lang)
  if not cc.has_function('printf', prefix : '#include<stdio.h>',
                         args : unit_test_args)
    error('"printf" function not found (should always exist).')
  endif

  # Should also be able to detect it without specifying the header
  # We check for a different function here to make sure the result is
  # not taken from a cache (ie. the check above)
  # On MSVC fprintf is defined as an inline function in the header, so it cannot
  # be found without the include.
  if cc.get_id() != 'msvc'
    assert(cc.has_function('fprintf', args : unit_test_args),
           '"fprintf" function not found without include (on !msvc).')
  else
    assert(cc.has_function('fprintf', prefix : '#include <stdio.h>',
                           args : unit_test_args),
           '"fprintf" function not found with include (on msvc).')
    # Compiler intrinsics
    assert(cc.has_function('strcmp'),
           'strcmp intrinsic should have been found on MSVC')
    assert(cc.has_function('strcmp', prefix : '#include <string.h>'),
           'strcmp intrinsic should have been found with #include on MSVC')
  endif

  if cc.has_function('hfkerhisadf', prefix : '#include<stdio.h>',
                     args : unit_test_args)
    error('Found non-existent function "hfkerhisadf".')
  endif

  if cc.has_function('hfkerhisadf', args : unit_test_args)
    error('Found non-existent function "hfkerhisadf".')
  endif

  # With glibc on Linux lchmod is a stub that will always return an error,
  # we want to detect that and declare that the function is not available.
  # We can't check for the C library used here of course, but if it's not
  # implemented in glibc it's probably not implemented in any other 'slimmer'
  # C library variants either, so the check should be safe either way hopefully.
  if host_system == 'linux' or host_system == 'darwin'
    assert (cc.has_function('poll', prefix : '#include <poll.h>',
                            args : unit_test_args),
            'couldn\'t detect "poll" when defined by a header')
    lchmod_prefix = '#include <sys/stat.h>\n#include <unistd.h>'
    if host_system == 'linux'
      assert (not cc.has_function('lchmod', prefix : lchmod_prefix,
                                  args : unit_test_args),
              '"lchmod" check should have failed')
    else
      # macOS and *BSD have lchmod
      assert (cc.has_function('lchmod', prefix : lchmod_prefix,
                                  args : unit_test_args),
              '"lchmod" check should have succeeded')
    endif
    # Check that built-ins are found properly both with and without headers
    assert(cc.has_function('alloca', args : unit_test_args),
           'built-in alloca must be found on ' + host_system)
    assert(cc.has_function('alloca', prefix : '#include <alloca.h>',
           args : unit_test_args),
           'built-in alloca must be found with #include')
    if not cc.compiles(defines_has_builtin, args : unit_test_args)
      assert(cc.has_function('alloca',
             prefix : '#include <alloca.h>\n#undef alloca',
             args : unit_test_args),
             'built-in alloca must be found with #include and #undef')
    endif
  endif

  # For some functions one needs to define _GNU_SOURCE before including the
  # right headers to get them picked up. Make sure we can detect these functions
  # as well without any prefix
  if cc.has_header_symbol('sys/socket.h', 'recvmmsg',
                          prefix : '#define _GNU_SOURCE',
                          args : unit_test_args)
    # We assume that if recvmmsg exists sendmmsg does too
    assert (cc.has_function('sendmmsg', args : unit_test_args),
            'Failed to detect function "sendmmsg" (should always exist).')
  endif

  # On MinGW, strndup was incorrectly detected as available with has_function
  # even though it is not, so if it is detected by has_function, assert that it
  # can actually be found by the linker.
  if cc.has_function('strndup', args : unit_test_args)
    assert(cc.has_function('strndup', prefix: '#include <string.h>', args : unit_test_args),
           'strndup not found with prefix')
    assert(cc.links('#include <string.h>\nint main() { char *s = strndup ("string", 1); }',
                    args : unit_test_args),
           'strndup incorrectly detected')
  endif

  # Test various builtins
  if ['gcc', 'clang'].contains(cc.get_id())
    # This is meant to be used as __builtin_smul_overflow, so we shouldn't find the unbuiltin version
    assert(cc.has_function('__builtin_smul_overflow', args : unit_test_args),
           '__builtin_smul_overflow must be found')
    # FIXME: this fails on gcc, and we can't fix it without breaking builtin
    # detection without headers for things like alloca()
    if cc.get_id() == 'clang'
      assert(not cc.has_function('smul_overflow', args : unit_test_args),
             'smul_overflow is __builtin_smul_overflow and must not be found')
    endif
    # Math builtins
    if lang == 'c'
      foreach bf: ['fpclassify', 'isfinite', 'isnormal', 'isgreater', 'isnan',
                   'isgreaterequal', 'isless', 'islessequal', 'islessgreater',
                   'isunordered']
        assert(cc.has_function(bf, prefix : '#include <math.h>', args : unit_test_args),
               '@0@ must be found'.format(bf))
      endforeach
    endif
    # String builtins
    foreach bf: ['strncpy', 'strncat', 'strcspn', 'strspn']
      assert(cc.has_function(bf, args : unit_test_args),
             '@0@ must be found'.format(bf))
    endforeach
    # Other builtins
    assert(cc.has_function('offsetof', prefix : '#include <stddef.h>', args : unit_test_args),
           'offsetof must be found')
    foreach bf: ['va_start', 'va_end', 'va_arg']
      assert(cc.has_function(bf, prefix : '#include <stdarg.h>', args : unit_test_args),
             '@0@ must be found'.format(bf))
    endforeach
  endif
endforeach
