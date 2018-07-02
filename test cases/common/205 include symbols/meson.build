project('test include_symbols with shared libraries', 'cpp')

cc = meson.get_compiler('cpp')

if cc.symbols_have_underscore_prefix()
  symbol_prefix = '_'
else
  symbol_prefix = ''
endif

registry_lib = shared_library('registry',
  'registry.cpp',
  install: false) # Don't install libraries in common tests; the path is platform-specific

plugin_lib = shared_library('plugin',
  'plugin.cpp',
  link_with: registry_lib,
  install: false) # Don't install libraries in common tests; the path is platform-specific


# first test: the plugin lib is NOT loaded if no symbols are manually included

exe1 = executable('exe1',
  'main.cpp',
  link_with: [registry_lib, plugin_lib],
  build_rpath: meson.current_build_dir()
)

test('test1', exe1, should_fail: true)


# second test: however, it IS, if we manually include at least one symbol from it

exe2 = executable('exe2',
  'main.cpp',
  link_with: [registry_lib, plugin_lib],
  include_symbols: symbol_prefix + 'plugin_dummy',
  build_rpath: meson.current_build_dir()
)

test('test2', exe2)

# TODO: test if more symbols are loaded (as a list), test with shared libraries,
# test transitivity, test what happens if plugin_lib is not linked with registry_lib
