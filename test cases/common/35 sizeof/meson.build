project('sizeof', 'c')

cc = meson.get_compiler('c')
intsize = cc.sizeof('int')

cd = configuration_data()
cd.set('INTSIZE', intsize)
configure_file(input : 'config.h.in', output : 'config.h', configuration : cd)

e = executable('prog', 'prog.c', include_dirs : include_directories('.'))
add_test('sizeof test', e)
