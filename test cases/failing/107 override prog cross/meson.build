project('override platform doesn\'t match')

if not meson.is_cross_build()
   error('MESON_SKIP_TEST test only applicable when cross building.')
endif

replacement = find_program('foo.py', required: false, native: true)
meson.override_find_program('bar.py', replacement, native: false)
