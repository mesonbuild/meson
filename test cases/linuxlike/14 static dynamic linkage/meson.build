project('static dynamic', 'c')


cc = meson.get_compiler('c')

z_default = cc.find_library('z')
z_static = cc.find_library('z', static: true)
z_dynamic = cc.find_library('z', static: false)

exe_default = executable('main_default', 'main.c', dependencies: [z_default])
exe_static = executable('main_static', 'main.c', dependencies: [z_static])
exe_dynamic = executable('main_dynamic', 'main.c', dependencies: [z_dynamic])

test('test default', exe_default)
test('test static', exe_static)
test('test dynamic', exe_dynamic)

test('verify static linking', find_program('verify_static.py'), args:exe_static.full_path())
test('verify dynamic linking', find_program('verify_static.py'), args:exe_dynamic.full_path(),
     should_fail: true)
