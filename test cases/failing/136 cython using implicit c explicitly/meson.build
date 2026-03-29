project(
  'cython leaking implementation details',
  default_options : ['warning_level=3', 'buildtype=release'],
)

if meson.backend() != 'ninja'
  error('MESON_SKIP_TEST: Ninja backend required')
endif

if not add_languages('cython', required : false)
  error('MESON_SKIP_TEST: Cython langauge required')
endif

static_library('foo', 'foo.c')
