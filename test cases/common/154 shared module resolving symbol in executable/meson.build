project('shared module resolving symbol in executable', 'c')

# The shared module contains a reference to the symbol 'func_from_executable',
# which is always provided by the executable which loads it.  This symbol can be
# resolved at run-time by an ELF loader.  But when building PE/COFF objects, all
# symbols must be resolved at link-time, so an implib is generated for the
# executable, and the shared module linked with it.
#
# See testcase 125 for an example of the more complex portability gymnastics
# required if we do not know (at link-time) what provides the symbol.

link_flags = []
if host_machine.system() != 'windows'
  # Needed to export dynamic symbols from the executable
  link_flags += ['-rdynamic']
  # Need to add this manually because Meson won't add it automatically because
  # it doesn't know that we are loading a module from the build directory.
  link_flags += ['-Wl,-rpath,' + meson.current_build_dir()]
endif

dl = meson.get_compiler('c').find_library('dl', required: false)
e = executable('prog', 'prog.c', dependencies: dl, implib: true, link_args: link_flags)
m = shared_module('module', 'module.c', link_with: e)
test('test', e, args: m)
