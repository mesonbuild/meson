project('simd', 'c')

cdata = configuration_data()

#cdata.set('HAVE_MMX', 1)

configure_file(output : 'simdconfig.h',
  configuration : cdata)

p = executable('simdtest', 'simdchecker.c', 'fallback.c')

test('simdtest', p)

