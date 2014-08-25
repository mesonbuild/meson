project('flex and bison', 'c')

# The point of this test is that one generator
# may output headers that are necessary to build
# the sources of a different generator.

flex = find_program('flex')
bison = find_program('bison')

lgen = generator(flex,
output : '@PLAINNAME@.yy.c',
arguments : ['-o', '@OUTPUT@', '@INPUT@'])

lfiles = lgen.process('lexer.l')

pgen = generator(bison,
output : ['@BASENAME@.tab.c', '@BASENAME@.tab.h'],
arguments : ['@INPUT@', '--defines=@OUTPUT1@', '--output=@OUTPUT0@'])

pfiles = pgen.process('parser.y')

e = executable('pgen', 'prog.c',
lfiles, pfiles)

test('parsertest', e)

