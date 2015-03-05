project('trickier generator', 'cpp')

comp = find_program('mygen.py')
subdir('subdir')

generated2 = custom_target('generated2',
output : ['source2.h', 'source2.cpp'],
input : 'data2.dat',
command : [comp, '@INPUT0@', meson.current_build_dir()])

exe = executable('prog', 'main.cpp', generated, generated2,
include_directories : include_directories('subdir'))
test('generated test', exe)
