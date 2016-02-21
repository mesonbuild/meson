if host_machine.system() == 'darwin'
  # Default suffix is 'dylib' but Python does not use for extensions.
  suffix = 'so'
else
  suffix = []
endif

pylib = shared_library('tachyon',
  'tachyon_module.c',
  dependencies : py3_dep,
  name_prefix : '',
  name_suffix : suffix)

pypathdir = meson.current_build_dir()
