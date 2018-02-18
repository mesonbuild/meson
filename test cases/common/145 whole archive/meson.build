project('whole archive', 'c')

add_project_arguments('-I' + meson.source_root(), language : 'c')

cc = meson.get_compiler('c')

if cc.get_id() == 'msvc'
  if cc.version().version_compare('<19')
    error('MESON_SKIP_TEST link_whole only works on VS2015 or newer.')
  endif
endif

# Test 1: link_whole keeps all symbols
# Make static func1
subdir('st_func1')
# Make shared func2 linking whole func1 archive
subdir('sh_func2_linked_func1')
# Link exe with shared library only
subdir('exe')
# Test that both func1 and func2 are accessible from shared library
test('prog', exe)

# Test 2: link_whole can be used instead of source list, see #2180
# Make static func2
subdir('st_func2')
# Link both func1 and func2 into same shared library
# which does not have any sources other than 2 static libraries
subdir('sh_only_link_whole')
# Link exe2 with shared library only
subdir('exe2')
# Test that both func1 and func2 are accessible from shared library
test('prog2', exe2)
