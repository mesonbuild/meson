project('preserve subdir', 'c')

gprog = find_program('genprog.py')

gen = generator(gprog, \
  output    : ['@BASENAME@.c', '@BASENAME@.h'],
  arguments : ['--searchdir=@CURRENT_SOURCE_DIR@', '--outdir=@BUILD_DIR@', '@INPUT@'])

generated = gen.process('base.inp', 'com/mesonbuild/subbie.inp',
  preserve_path_from : meson.current_source_dir())

e = executable('testprog', 'testprog.c', generated)
test('testprog', e)
