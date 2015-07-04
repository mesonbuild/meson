project('same basename', 'c')

stlib = static_library('name', 'stat.c')
shlib = shared_library('name', 'shar.c')

exe1 = executable('name', 'exe1.c', link_with : stlib)
exe2 = executable('name2', 'exe2.c', link_with : shlib)

test('static', exe1)
test('shared', exe2)
