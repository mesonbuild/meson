project('all sources generated', 'c')

comp = find_program('converter.py')

g = generator(comp,
  output : '@BASENAME@.c',
  arguments : ['@INPUT@', '@OUTPUT@'])

c = g.process('foobar.c.in')

prog = executable('genexe', c)
