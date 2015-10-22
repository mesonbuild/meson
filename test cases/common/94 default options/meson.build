project('default options', 'cpp', 'c', default_options : [
  'buildtype=debugoptimized',
  'cpp_std=c++03',
  'cpp_eh=none',
  'c_std=-crashcompiler',
  ])

cpp = meson.get_compiler('cpp')

assert(get_option('buildtype') == 'debugoptimized', 'Build type default value wrong.')

if cpp.get_id() == 'msvc'
  assert(get_option('cpp_eh') == 'none', 'MSVC eh value wrong.')
else
  assert(get_option('cpp_std') == 'c++03', 'C++ std value wrong.')
endif

# Verify that project args are not used when told not to.
# MSVC plain C does not have a simple arg to test so skip it.
if cpp.get_id() != 'msvc'
  cc = meson.get_compiler('c')
  assert(not cc.compiles('int foobar;'), 'Default arg not used in test.')
  assert(cc.compiles('int foobar;', no_builtin_args : true), 'No_builtin did not disable builtins.')
endif

