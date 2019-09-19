project('test static link', 'c')

cc = meson.get_compiler('c')

# Verify that installed libfunc2.a is usable
func2_dep = cc.find_library('func2')
test('test1', executable('test1', 'test1.c', dependencies : func2_dep))
