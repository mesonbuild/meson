project('pipeline test', 'c')

e1 = executable('srcgen', 'srcgen.c')

gen = generator(e1, \
 output_name  : '@BASENAME@.c', \
 arguments : ['@INPUT@', '@OUTPUT@'])

generated = gen.process('input_src.dat')

e2 = executable('prog', 'prog.c', gen_src : generated)

add_test('pipelined', e2)
