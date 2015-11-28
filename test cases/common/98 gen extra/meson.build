project('extra args in gen', 'c')

prog = find_program('srcgen.py')

gen = generator(prog,
  output : '@BASENAME@.c',
  arguments : ['--input=@INPUT@', '--output=@OUTPUT@', '@EXTRA_ARGS@'])

g1 = gen.process('name.dat')
g2 = gen.process('name.dat', extra_args: '--upper')

test('basic', executable('basic', 'plain.c', g1))
test('upper', executable('upper', 'upper.c', g2))
