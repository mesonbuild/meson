project('linker script', 'c')

vflag = '-Wl,--version-script,@0@/bob.map'.format(meson.current_source_dir())

l = shared_library('bob', 'bob.c', link_flags : vflag)
e = executable('prog', 'prog.c', link_with : l)
test('core', e)
