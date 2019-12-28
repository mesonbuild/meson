project('cmMod', ['c', 'cpp'])

cm       = import('cmake')
cmMod    = cm.subproject('cmMod')
cmModDep = cmMod.dependency('cmModLib')

exe1 = executable('exe1', ['main.cpp'], dependencies: [cmModDep])
test('exe1_OK', exe1)
