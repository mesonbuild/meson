project('cmakeSubTest', ['c', 'cpp'])

cm = import('cmake')
sub_pro = cm.subproject('cmMod')

# Compile one first exe to ensure the library is built
sub_internal = sub_pro.dependency('cmModLib_internal', include_type: 'system')
exe0 = executable('main0', ['main.cpp'], dependencies: [sub_internal])

# use the library through a config file
sub_config = sub_pro.dependency('cmModLib++', include_type: 'system')
exe1 = executable('main', ['main.cpp'], dependencies: [sub_config], link_depends: [exe0])
test('test1', exe1)
