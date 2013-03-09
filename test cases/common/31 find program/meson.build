project('find program', 'c')

cp = find_program('cp', required : true)


gen = generator(cp, \
 output_name  : '@BASENAME@.c', \
 arguments : ['@INPUT@', '@OUTPUT@'])

generated = gen.process('source.in')
e = executable('prog', generated)
add_test('external exe', e)
