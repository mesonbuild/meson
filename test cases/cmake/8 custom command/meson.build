project('cmakeSubTest', ['c', 'cpp'])

cm = import('cmake')

sub_pro = cm.subproject('cmMod')
sub_dep = sub_pro.dependency('cmModLib')

assert(sub_pro.target_type('cmModLib') == 'shared_library', 'Target type should be shared_library')
assert(sub_pro.target_type('gen') == 'executable', 'Target type should be executable')

exe1 = executable('main', ['main.cpp'], dependencies: [sub_dep])
test('test1', exe1)
