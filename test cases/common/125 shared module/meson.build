project('shared module', 'c')

dl = meson.get_compiler('c').find_library('dl', required : false)
l = shared_library('runtime', 'runtime.c')
if host_machine.system() == 'darwin' or host_machine.system() == 'windows'
  # At least in OSX and seemingly also on Windows you must have
  # all symbols present when linking a module.
  #
  # In Linux many projects build plugins without linking to
  # the runtime so they have undefined symbols. We need to support
  # both for ease of transitioning.
  mlink = [l]
else
  mlink = []
endif
m = shared_module('mymodule', 'module.c', link_with : mlink)
e = executable('prog', 'prog.c', link_with : l, dependencies : dl)
test('import test', e, args : [m.full_path()])

