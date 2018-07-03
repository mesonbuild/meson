project('hidden symbol', 'c')

if host_machine.system() == 'windows'
  cc = meson.get_compiler('c')
  if cc.get_id() == 'gcc'
    error('MESON_SKIP_TEST -fvisibility=hidden does not work on MinGW.')
  endif
endif

l = shared_library('bob', 'bob.c',
  symbol_visibility: 'hidden')

executable('bobuser', 'bobuser.c',
  link_with: l)
