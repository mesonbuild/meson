project('test', default_options: ['warning_level=3', 'werror=true'])
if not add_languages('fortran', required: false)
  error('MESON_SKIP_TEST: Fortran not found')
endif
executable('prog', 'test.f90')
