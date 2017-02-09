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

simdlibs = []

if cc.has_argument('-mmmx')
  cdata.set('HAVE_MMX', 1)
  simdlibs += static_library('simd_mmx', 'simd_mmx.c', c_args : '-mmmx')
endif

configure_file(output : 'simdconfig.h',
  configuration : cdata)

p = executable('simdtest', 'simdchecker.c', 'fallback.c',
  link_with : simdlibs)

test('simdtest', p)

