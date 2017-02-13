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
#<tmmintrin.h> SSSE3
#<smmintrin.h> SSE4.1
#<nmmintrin.h> SSE4.2
#<ammintrin.h> SSE4A
#<wmmintrin.h> AES
#<immintrin.h> AVX
#<zmmintrin.h> AVX512

simdlibs = []

simdarr = [['-mmmx', 'HAVE_MMX', 'simd_mmx', 'simd_mmx.c'],
 ['-msse', 'HAVE_SSE', 'simd_sse', 'simd_sse.c'],
 ['-msse2', 'HAVE_SSE2', 'simd_sse2', 'simd_sse2.c'],
 ['-msse3', 'HAVE_SSE3', 'simd_sse3', 'simd_sse3.c'],
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

