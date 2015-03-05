project('sizeof', 'c')

cc = meson.get_compiler('c')
intsize = cc.sizeof('int')
wcharsize = cc.sizeof('wchar_t', prefix : '#include<wchar.h>')

cd = configuration_data()
cd.set('INTSIZE', intsize)
cd.set('WCHARSIZE', wcharsize)
configure_file(input : 'config.h.in', output : 'config.h', configuration : cd)

e = executable('prog', 'prog.c')
test('sizeof test', e)
