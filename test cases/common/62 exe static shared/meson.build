project('statchain', 'c')

subdir('subdir')
statlib = static_library('stat', 'stat.c', link_with : shlib, pic : true)
shlib2 = shared_library('shr2', 'shlib2.c', link_with : statlib)
exe = executable('prog', 'prog.c', link_with : shlib2)
test('runtest', exe)
