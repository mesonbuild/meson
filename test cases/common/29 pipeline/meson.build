project('pipeline test', 'c')

e1 = executable('srcgen', 'srcgen.c')

gen = generator(e1, \
 outputs  : '@BASENAME@.c', # Line continuation inside arguments should work without needing a "\".
 arguments : ['@INPUT@', '@OUTPUT@'])

generated = gen.process('input_src.dat')

e2 = executable('prog', 'prog.c', generated)

test('pipelined', e2)
