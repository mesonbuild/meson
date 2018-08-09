project('hidden symbol', 'c')

if host_machine.system() == 'windows' or host_machine.system() == 'cygwin'
  cc = meson.get_compiler('c')
  if cc.get_id() == 'gcc'
    error('MESON_SKIP_TEST -fvisibility=hidden does not work on MinGW or Cygwin.')
  endif
endif

l = shared_library('bob', 'bob.c',
  gnu_symbol_visibility: 'hidden')

executable('bobuser', 'bobuser.c',
  link_with: l)
