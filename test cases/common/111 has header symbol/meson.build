project('has header symbol', 'c')

cc = meson.get_compiler('c')

assert (cc.has_header_symbol('stdio.h', 'int'), 'base types should always be available')
assert (cc.has_header_symbol('stdio.h', 'printf'), 'printf function not found')
assert (cc.has_header_symbol('stdio.h', 'FILE'), 'FILE structure not found')
assert (cc.has_header_symbol('limits.h', 'INT_MAX'), 'INT_MAX define not found')
assert (not cc.has_header_symbol('limits.h', 'guint64'), 'guint64 is not defined in limits.h')
assert (not cc.has_header_symbol('stdlib.h', 'FILE'), 'FILE structure is defined in stdio.h, not stdlib.h')
assert (not cc.has_header_symbol('stdlol.h', 'printf'), 'stdlol.h shouldn\'t exist')
assert (not cc.has_header_symbol('stdlol.h', 'int'), 'shouldn\'t be able to find "int" with invalid header')

# This is likely only available on Glibc, so just test for it
if cc.has_function('ppoll')
  assert (not cc.has_header_symbol('poll.h', 'ppoll'), 'ppoll should not be accessible without _GNU_SOURCE')
  assert (cc.has_header_symbol('poll.h', 'ppoll', prefix : '#define _GNU_SOURCE'), 'ppoll should be accessible with _GNU_SOURCE')
endif
