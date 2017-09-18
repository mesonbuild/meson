project('extra args in gen', 'c')

prog = find_program('srcgen.py')

gen = generator(prog,
  output : '@BASENAME@.c',
  arguments : ['--input=@INPUT@', '--output=@OUTPUT@', '@EXTRA_ARGS@'])

g1 = gen.process('name.dat')
g2 = gen.process('name.dat', extra_args: '--upper')

test('basic', executable('basic', 'plain.c', g1))
test('upper', executable('upper', 'upper.c', g2))

cp = find_program('cp')
basename_gen = generator(cp,
  output : '@BASENAME@.c',
  arguments : ['@INPUT@', join_paths('@BUILD_DIR@', '@BASENAME@.c')])

# This test should produce a name.c
basename_src = basename_gen.process('name.l')

test('basename', executable('basename', basename_src))

plainname_gen = generator(cp,
  output : '@PLAINNAME@.c',
  arguments : ['@INPUT@', join_paths('@BUILD_DIR@', '@PLAINNAME@.c')])

# This test should produce a name.l.c
plainname_src = plainname_gen.process('name.l')

test('plainname', executable('plainname', plainname_src))
