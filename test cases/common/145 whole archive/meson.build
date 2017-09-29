project('whole archive', 'c')

add_project_arguments('-I' + meson.source_root(), language : 'c')

cc = meson.get_compiler('c')

if cc.get_id() == 'msvc'
  if cc.version().version_compare('<19')
    error('MESON_SKIP_TEST link_whole only works on VS2015 or newer.')
  endif
endif

subdir('allofme')
subdir('shlib')
subdir('exe')

test('prog', exe)

# link_whole only
subdir('stlib')
subdir('wholeshlib')
subdir('exe2')

test('prog2', exe2)
