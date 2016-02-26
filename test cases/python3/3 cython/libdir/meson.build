if host_machine.system() == 'darwin'
  # Default suffix is 'dylib' but Python does not use for extensions.
  suffix = 'so'
elif host_machine.system() == 'windows'
  # On Windows the extension is pyd for some unexplainable reason.
  suffix = 'pyd'
else
  suffix = []
endif

pyx_c = custom_target('storer_pyx',
  output : 'storer_pyx.c',
  input : 'storer.pyx',
  command : [cython, '@INPUT@', '-o', '@OUTPUT@'],
)

slib = shared_library('storer',
  'storer.c', pyx_c,
  name_prefix : '',
  name_suffix : suffix,
  dependencies : py3_dep)

pydir = meson.current_build_dir()
