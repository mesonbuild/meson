project('test link_whole with shared libraries', 'cpp')


registry_lib = shared_library('registry',
  'registry.cpp',
  install: false) # Don't install libraries in common tests; the path is platform-specific


plugin_lib = shared_library('plugin',
  'plugin.cpp',
  link_with: registry_lib, # no need for link_whole here
  install: false) # Don't install libraries in common tests; the path is platform-specific


# first test: the plugin lib does NOT get loaded if link_with is used

exe1 = executable('exe1',
  'main.cpp',
  link_with: [registry_lib, plugin_lib],
  build_rpath: meson.current_build_dir(),
  install: true)

test('test1', exe1, should_fail: true)

# second test: however, it DOES, if link_whole is used instead

exe2 = executable('exe2',
  'main.cpp',
  link_with: registry_lib,
  link_whole: plugin_lib,
  build_rpath: meson.current_build_dir(),
  install: true)

test('test2', exe2)
