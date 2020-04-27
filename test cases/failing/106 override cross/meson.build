project('override platform doesn\'t match')

if not meson.is_cross_build()
   error('MESON_SKIP_TEST test only applicable when cross building.')
endif

replacement = dependency('foo', required: false, native: true)
meson.override_dependency('bar', replacement, native: false)
