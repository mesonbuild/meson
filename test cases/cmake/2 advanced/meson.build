project('cmakeSubTest_advanced', ['cpp'])

# Test the "normal" subproject call
sub_pro = subproject('cmMod')
sub_dep = sub_pro.get_variable('cmModLib_dep')

# Test the dependency shortcut
shortcut_dep = dependency('ttabadbneiobevn', fallback: ['cmMod', 'cmModLib_dep'])

# Build some files
exe1 = executable('main1', ['main.cpp'], dependencies: [sub_dep])
exe2 = executable('main2', ['main.cpp'], dependencies: [shortcut_dep])
test('test1', exe1)
test('test2', exe2)

# Test if we can also extract executables
test('test3', sub_pro.get_variable('testEXE'))
