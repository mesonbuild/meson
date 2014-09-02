project('statchain', 'c')

subdir('subdir')
statlib = static_library('stat', 'stat.c', link_with : shlib)
exe = executable('prog', 'prog.c', link_with : statlib)
test('runtest', exe)
