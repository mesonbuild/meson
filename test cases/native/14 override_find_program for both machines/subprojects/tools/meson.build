project('tools', 'c')

exe = executable('mytool', 'mytool.c')

if meson.can_run_host_binaries()
  meson.override_find_program('mytool', exe)
  # In a cross build, the copy of the subproject for the build machine provides
  # the program for the build machine.
  if not meson.is_cross_build()
    meson.override_find_program('mytool', exe, native : true)
  endif
endif
