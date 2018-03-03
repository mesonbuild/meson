# Must have two languages here to exercise linker language
# selection bug
project('all sources generated', 'c', 'cpp')

comp = find_program('converter.py')

g = generator(comp,
  outputs : ['@BASENAME@.h', '@BASENAME@.cpp'],
  arguments : ['@INPUT@'])

c = g.process('foobar.cfg')
prog = executable('genexe', c)
