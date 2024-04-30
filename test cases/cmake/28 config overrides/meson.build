project('cmakeSubTest', ['c', 'cpp'])

cm = import('cmake')
sub_pro = cm.subproject('cmMod')

# TODO: CMake add_dependency does not work with INTERFACE targets
# Ensure that all targets are built
tgt_internal = sub_pro.target('cmModLib_internal')
tgt_test2 = sub_pro.target('test2')

# use the library through a config file
sub_config = sub_pro.dependency('cmModLib++', include_type: 'system')
exe1 = executable('main', ['main.cpp'], dependencies: [sub_config],
  link_depends: [tgt_internal, tgt_test2])
test('test1', exe1)
