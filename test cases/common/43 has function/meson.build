project('has function', 'c', 'cpp')

host_system = host_machine.system()

# This is used in the `test_compiler_check_flags_order` unit test
unit_test_args = '-I/tmp'
compilers = [meson.get_compiler('c'), meson.get_compiler('cpp')]

foreach cc : compilers
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
  if host_system == 'linux'
    assert (cc.has_function('poll', prefix : '#include <poll.h>',
                            args : unit_test_args),
            'couldn\'t detect "poll" when defined by a header')
    lchmod_prefix = '#include <sys/stat.h>\n#include <unistd.h>'
    assert (not cc.has_function('lchmod', prefix : lchmod_prefix,
                                args : unit_test_args),
            '"lchmod" check should have failed')
    # Check that built-ins are found properly both with and without headers
    assert(cc.has_function('alloca', args : unit_test_args),
           'built-in alloca must be found on Linux')
    assert(cc.has_function('alloca', prefix : '#include <alloca.h>',
           args : unit_test_args),
           'built-in alloca must be found on Linux with #include')
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
endforeach
