project('cmakeSubTest', ['cpp'])

sub_pro = subproject('cmMod', method: 'cmake')
sub_dep = sub_pro.get_variable('cmModLib_dep')

exe1 = executable('main', ['main.cpp'], dependencies: [sub_dep])
test('test1', exe1)
