project('simd', 'c')

cc = meson.get_compiler('c')

cdata = configuration_data()

# The idea is to have a simd module and then do something like:
#
# static_libs = simd.check('mysimdstuff',
#   mmx : 'mmx_funcs.c',
#   sse : 'sse_funcs.c',
#   sse2 : 'sse2_funcs.c',
#   <etc>
#   configuration : cdata, # adds HAVE_XXX
#   compiler : cc)
#
# and then have a target that uses the result in links_with.

# The following headers need to be added. Also Thumb and Altivec.
#<emmintrin.h> SSE2
#<pmmintrin.h> SSE3
#<tmmintrin.h> SSSE3
#<smmintrin.h> SSE4.1
#<nmmintrin.h> SSE4.2
#<ammintrin.h> SSE4A
#<wmmintrin.h> AES
#<immintrin.h> AVX
#<zmmintrin.h> AVX512

simdlibs = []

if cc.has_argument('-mmmx')
  cdata.set('HAVE_MMX', 1)
  simdlibs += static_library('simd_mmx', 'simd_mmx.c', c_args : '-mmmx')
endif

if cc.has_argument('-msse')
  cdata.set('HAVE_SSE', 1)
  simdlibs += static_library('simd_sse', 'simd_sse.c', c_args : '-msse')
endif

configure_file(output : 'simdconfig.h',
  configuration : cdata)

p = executable('simdtest', 'simdchecker.c', 'fallback.c',
  link_with : simdlibs)

test('simdtest', p)

