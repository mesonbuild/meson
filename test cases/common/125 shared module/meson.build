project('shared module', 'c')

dl = meson.get_compiler('c').find_library('dl', required : false)
l = shared_library('runtime', 'runtime.c')
m = shared_module('mymodule', 'module.c')
e = executable('prog', 'prog.c', link_with : l, dependencies : dl)
test('import test', e, args : [m.full_path()])

