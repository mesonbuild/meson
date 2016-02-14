pyx_c = custom_target('storer_pyx',
  output : 'storer_pyx.c',
  input : 'storer.pyx',
  command : [cython, '@INPUT@', '-o', '@OUTPUT@'],
)

slib = shared_library('storer',
  'storer.c', pyx_c,
  name_prefix : '',
  dependencies : py3_dep)

pydir = meson.current_build_dir()
