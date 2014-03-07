project('linker script', 'c')

vflag = '-Wl,--version-script,@0@/bob.map'.format('/home/jpakkane/workspace/meson/test cases/linuxlike/3 linker script')

l = shared_library('bob', 'bob.c', link_flags : vflag)
e = executable('prog', 'prog.c', link_with : l)
test('core', e)
