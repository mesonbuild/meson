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
#<wmmintrin.h> AES
#<zmmintrin.h> AVX512

simdlibs = []

simdarr = [['-mmmx', 'HAVE_MMX', 'simd_mmx', 'simd_mmx.c'],
 ['-msse', 'HAVE_SSE', 'simd_sse', 'simd_sse.c'],
 ['-msse2', 'HAVE_SSE2', 'simd_sse2', 'simd_sse2.c'],
 ['-msse3', 'HAVE_SSE3', 'simd_sse3', 'simd_sse3.c'],
 ['-mssse3', 'HAVE_SSSE3', 'simd_ssse3', 'simd_ssse3.c'],
 ['-msse4.1', 'HAVE_SSE41', 'simd_sse41', 'simd_sse41.c'],
 ['-msse4.2', 'HAVE_SSE42', 'simd_sse42', 'simd_sse42.c'],
 ['-mavx', 'HAVE_AVX', 'simd_avx', 'simd_avx.c'],
 ['-mavx2', 'HAVE_AVX2', 'simd_avx2', 'simd_avx2.c'],
]

foreach ia : simdarr
  arg = ia[0]
  def = ia[1]
  libname = ia[2]
  filename = ia[3]
  if cc.has_argument(arg)
    cdata.set(def, 1)
    simdlibs += static_library(libname, filename, c_args : arg)
  endif
endforeach

configure_file(output : 'simdconfig.h',
  configuration : cdata)

p = executable('simdtest', 'simdchecker.c', 'fallback.c',
  link_with : simdlibs)

test('simdtest', p)

