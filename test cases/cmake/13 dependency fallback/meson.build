project('cmakeSubTest', ['c', 'cpp'])

sub_dep = dependency('', fallback : ['cmMod', 'cmModLib_dep'])
exe1 = executable('main', ['main.cpp'], dependencies: [sub_dep])
test('test1', exe1)
