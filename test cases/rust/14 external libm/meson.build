project('rust linking to libm', 'c', 'rust')

cc = meson.get_compiler('c')
dep_m = cc.find_library('m', required : false, static : get_option('static'))
if not dep_m.found()
  error('MESON_SKIP_TEST: Could not find a @0@ libm'.format(get_option('static') ? 'static' : 'shared'))
endif

librs_math = static_library(
  'rs_math',
  'rs_math.rs',
  dependencies : [dep_m],
)

e = executable(
  'prog', 'prog.rs',
  link_with : [librs_math],
)

test('cdepstest', e)
