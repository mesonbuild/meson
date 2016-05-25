project('has function', 'c')

cc = meson.get_compiler('c')

if not cc.has_function('printf', prefix : '#include<stdio.h>')
  error('"printf" function not found (should always exist).')
endif

# Should also be able to detect it without specifying the header
# We check for a different function here to make sure the result is
# not taken from a cache (ie. the check above)
# On MSVC fprintf is defined as an inline function in the header, so it cannot
# be found without the include.
if cc.get_id() != 'msvc'
  assert(cc.has_function('fprintf'), '"fprintf" function not found without include (on !msvc).')
else
  assert(cc.has_function('fprintf', prefix : '#include <stdio.h>'), '"fprintf" function not found with include (on msvc).')
endif

if cc.has_function('hfkerhisadf', prefix : '#include<stdio.h>')
  error('Found non-existent function "hfkerhisadf".')
endif

# With glibc on Linux lchmod is a stub that will always return an error,
# we want to detect that and declare that the function is not available.
# We can't check for the C library used here of course, but if it's not
# implemented in glibc it's probably not implemented in any other 'slimmer'
# C library variants either, so the check should be safe either way hopefully.
if host_machine.system() == 'linux' and cc.get_id() == 'gcc'
  assert (cc.has_function('poll', prefix : '#include <poll.h>'), 'couldn\'t detect "poll" when defined by a header')
  assert (not cc.has_function('lchmod', prefix : '''#include <sys/stat.h>
                                                    #include <unistd.h>'''), '"lchmod" check should have failed')
endif

# For some functions one needs to define _GNU_SOURCE before including the
# right headers to get them picked up. Make sure we can detect these functions
# as well without any prefix
if cc.has_header_symbol('sys/socket.h', 'recvmmsg', prefix : '#define _GNU_SOURCE')
  # We assume that if recvmmsg exists sendmmsg does too
  assert (cc.has_function('sendmmsg'), 'Failed to detect function "sendmmsg" (should always exist).')
endif
