project('shared module', 'c')
compiler = meson.get_compiler('c')
have_undefsymbols = false

if not have_undefsymbols
  error('MESON_SKIP_TEST undefsymbols not supported on this platform.')
endif

# Link the static library with the executable only, and check that the
# functions brought in by the module are included in the executable.
l1 = static_library('runtime1', 'runtime1.c')
l2 = shared_library('runtime2', 'runtime2.c')

dl = compiler.find_library('dl', required : false)
e = executable('prog', 'prog.c',
  link_with : [l1, l2], implib: true, dependencies : dl)

# For this test, we link the module with the runtime library.
m = shared_module('mymodule', 'module.c', link_with: [e, l2])
test('import test', e, args : m)
