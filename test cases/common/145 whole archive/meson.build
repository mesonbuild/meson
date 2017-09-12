project('whole archive', 'c')

cc = meson.get_compiler('c')

if cc.get_id() == 'msvc'
  if cc.version().version_compare('<19')
    error('MESON_SKIP_TEST link_whole only works on VS2015 or newer.')
  endif
endif

stlib = static_library('allofme', 'libfile.c')

# Nothing in dylib.c uses func1, so the linker would throw it
# away and thus linking the exe would fail.
dylib = shared_library('shlib', 'dylib.c',
  link_whole : stlib)

exe = executable('prog', 'prog.c',
  link_with : dylib)

test('prog', exe)

# link_whole only
static = static_library('static', 'dylib.c')
dylib2 = shared_library('link_whole', link_whole : [stlib, static])

exe2 = executable('prog2', 'prog.c', link_with : dylib2)

test('prog2', exe2)
