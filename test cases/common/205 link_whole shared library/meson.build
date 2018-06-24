project('test link_whole with shared libraries', 'cpp')

# The only reason we use shared_module instead of shared_library is to avoid
# passing -Wl,--no-undefined to g++ (or the equivalent for other compilers),
# which would prevent the plugin library to use the extern variable defined
# only in the executable that will load it.

plugin_lib = shared_module('pluginlib',
  'pluginlib.cpp',
  install: false) # Don't install libraries in common tests; the path is platform-specific


# first test: the plugin lib does NOT get loaded if link_with is used

exe1 = executable('exe1',
  'main1.cpp',
  link_with: plugin_lib,
  build_rpath: meson.current_build_dir(),
  install: true)

test('test1', exe1, should_fail: true)

# second test: however, it DOES, if link_whole is used instead

exe2 = executable('exe2',
  'main1.cpp',
  link_whole: plugin_lib,
  build_rpath: meson.current_build_dir(),
  install: true)

test('test2', exe2)

# third test: this also works if another shared lib (middle) loads the plugin

middle_lib = shared_module('middlelib',
  'middlelib.cpp',
  link_whole: plugin_lib,
  build_rpath: meson.current_build_dir(),
  install: false) # Don't install libraries in common tests; the path is platform-specific

exe3 = executable('exe3',
  'main2.cpp',
  link_with: middle_lib, # no need to use link_whole here
  build_rpath: meson.current_build_dir(),
  install: true)

test('test3', exe3)
