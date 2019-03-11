project(
  'native file install dir override',
  default_options : ['default_library=static'],
)

if meson.is_cross_build()
  error('MESON_SKIP_TEST cannot test native build rules in cross build')
endif

assert(get_option('buildtype') == 'release', 'buildtype not changed')
assert(get_option('strip') == true, 'strip not changed')
assert(get_option('unity') == 'on', 'unity not changed')
assert(get_option('werror') == false, 'werror not changed')
assert(get_option('default_library') == 'both', 'default_library not changed')
assert(get_option('auto_features').disabled(), 'autofeatures not changed')
