project('as-needed test', 'cpp')

# Idea behind this test is to have -Wl,--as-needed prune
# away unneeded linkages, which would otherwise cause global
# static initialiser side-effects to set a boolean to true.

# Credits for portable ISO C++ idea go to sarum9in

libA = library('A', 'libA.cpp')
libB = library('B', 'libB.cpp', link_with : libA)

main_exe = executable('C', 'main.cpp', link_with : [libA, libB])
test('main test', main_exe)
