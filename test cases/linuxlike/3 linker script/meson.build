project('linker script', 'c')

mapfile = 'bob.map'
vflag = '-Wl,--version-script,@0@/@1@'.format(meson.current_source_dir(), mapfile)

l = shared_library('bob', 'bob.c', link_args : vflag, link_depends : mapfile)
e = executable('prog', 'prog.c', link_with : l)
test('core', e)
