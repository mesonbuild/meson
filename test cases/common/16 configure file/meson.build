project('configure file test', 'c')

conf = configuration_data()

conf.set('var', 'mystring')
conf.set('other', 'string 2')
conf.set('second', ' bonus')
conf.set('BE_TRUE', true)

configure_file(input : 'config.h.in',
output : 'config.h',
configuration : conf)

e = executable('inctest', 'prog.c', include_dirs : include_directories('.'))
test('inctest', e)
