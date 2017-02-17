project('simd', 'c')

simd = import('simd')

cc = meson.get_compiler('c')

cdata = configuration_data()

simdlibs = simd.check('mysimds',
  mmx : 'simd_mmx.c',
  sse : 'simd_sse.c',
  sse2 : 'simd_sse2.c',
  sse3 : 'simd_sse3.c',
  ssse3 : 'simd_ssse3.c',
  sse41 : 'simd_sse41.c',
  sse42 : 'simd_sse42.c',
  avx : 'simd_avx.c',
  avx2 : 'simd_avx2.c',
  neon : 'simd_neon.c',
  configuration : cdata,
  compiler : cc)


configure_file(output : 'simdconfig.h',
  configuration : cdata)

p = executable('simdtest', 'simdchecker.c', 'fallback.c',
  link_with : simdlibs)

test('simdtest', p)

