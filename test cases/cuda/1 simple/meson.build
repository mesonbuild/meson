project('simple', 'cuda', version : '1.0.0')

# https://github.com/mesonbuild/meson/issues/13240
d = meson.get_compiler('cuda').find_library('doesnotexist', required : false)
assert(not d.found())

exe = executable('prog', 'prog.cu')
test('cudatest', exe)
