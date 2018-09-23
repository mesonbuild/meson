project('dub', 'd', meson_version: '0.48.0')

if meson.get_compiler('d').get_id() == 'dmd'
  if host_machine.system() == 'windows' or host_machine.system() == 'cygwin'
    error('MESON_SKIP_TEST Windows test environment lacks multiple D compilers.')
  endif
endif

dependency('dubtestproject:test2', method: 'dub') # Compiler mismatch
