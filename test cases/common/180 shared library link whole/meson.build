project('whole archive', 'c')

cc = meson.get_compiler('c')

if cc.get_id() == 'msvc'
  if cc.version().version_compare('<19')
    error('MESON_SKIP_TEST link_whole only works on VS2015 or newer.')
  endif
endif

static1 = static_library('static1', 'static1.c')
static2 = static_library('static2', 'static2.c')

shared = shared_library('shared', 'shared.c', link_whole : [static1, static2])
exe = executable('exe', 'test.c', link_with : shared)
test('prog', exe)
