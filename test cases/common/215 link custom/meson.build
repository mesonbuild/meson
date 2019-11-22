project('linkcustom', 'c')

# This would require passing the static linker to the build script or having
# it detect it by itself. I'm too lazy to implement it now and it is not
# really needed for testing that custom targets work. It is the responsibility
# of the custom target to produce things in the correct format.
assert(not meson.is_cross_build(),
       'MESON_SKIP_TEST cross checking not implemented.')

cc = meson.get_compiler('c')
genprog = find_program('custom_stlib.py')

clib = custom_target('linkcustom',
  output: 'libflob.a',
  command: [genprog,
            '-o', '@OUTPUT@',
            '--private-dir', '@PRIVATE_DIR@'] + cc.cmd_array())

# custom_target tests

exe = executable('prog', 'prog.c', link_with: clib)
test('linkcustom', exe)

d = declare_dependency(link_with: clib)

exe2 = executable('prog2', 'prog.c', dependencies: d)
test('linkcustom2', exe2)

# Link whole tests

exe3 = executable('prog3', 'prog.c', link_whole: clib)
test('linkwhole', exe)

d2 = declare_dependency(link_whole: clib)

exe4 = executable('prog4', 'prog.c', dependencies: d2)
test('linkwhole2', exe2)

# custom_target[i] tests

exe_i = executable('prog_i', 'prog.c', link_with: clib[0])
test('linkcustom', exe_i)

d_i = declare_dependency(link_with: clib[0])

exe2_i = executable('prog2_i', 'prog.c', dependencies: d_i)
test('linkcustom2_i', exe2_i)

shared_library('lib1', 'lib.c', link_whole: clib)

# Link whole tests

exe3_i = executable('prog3_i', 'prog.c', link_whole: clib[0])
test('linkwhole', exe)

d2_i = declare_dependency(link_whole: clib[0])

exe4_i = executable('prog4_i', 'prog.c', dependencies: d2_i)
test('linkwhole2_i', exe2_i)
