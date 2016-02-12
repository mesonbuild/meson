pxd_c = custom_target('cstorer_pxd',
  output : 'cstorer_pxd.c',
  input : 'cstorer.pxd',
  command : [cython, '@INPUT@', '-o', '@OUTPUT@'],
)

pyx_c = custom_target('storer_pyx',
  output : 'storer_pyx.c',
  input : 'storer.pyx',
  command : [cython, '@INPUT@', '-o', '@OUTPUT@'],
)

slib = shared_library('storer',
  'storer.c', pxd_c, pyx_c,
  name_prefix : '',
  dependencies : py3_dep)

pydir = meson.current_build_dir()
