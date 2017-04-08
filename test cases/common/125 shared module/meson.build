project('shared module', 'c')

dl = meson.get_compiler('c').find_library('dl', required : false)
l = shared_library('runtime', 'runtime.c')
# Do NOT link the module with the runtime library. This
# is a common approach for plugins that are only used
# with dlopen. Any symbols are resolved dynamically
# at runtime.  This requires extra help on Windows, so
# should be avoided unless really neccessary.
m = shared_module('mymodule', 'module.c')
e = executable('prog', 'prog.c', link_with : l, dependencies : dl)
test('import test', e, args : m)

