project('prebuilt shared library', 'c')

cc = meson.get_compiler('c')
shlib = cc.find_library('alexandria', dirs : meson.current_source_dir())

exe = executable('patron', 'patron.c', dependencies : shlib)
test('visitation', exe)

d = declare_dependency(dependencies : shlib)

exe2 = executable('another_visitor', 'another_visitor.c',
  dependencies : d)
test('another', exe2)

