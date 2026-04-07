project('val2', 'c')
val1_dep = dependency('val1')
val2 = shared_library('val2', 'val2.c',
  dependencies : [val1_dep],
  install: true)
install_headers('val2.h')
pkgconfig = import('pkgconfig')

# linuxliketests.py will leave val1.pc out of the PKG_CONFIG_PATH,
# to check that requires_shared: [] removes it from Requires.private
pkgconfig.generate(val2, libraries : ['-Wl,-rpath,${libdir}'],
  requires_shared: [])
