project('has header', 'c')

cc = meson.get_compiler('c')

conf = configuration_data()
cc.has_header('stdio.h', configuration : conf)
cfile = configure_file(input : 'config.h.in',
output : 'config.h',
configuration : conf)

test('inctest', executable('inctest', 'prog.c'))
