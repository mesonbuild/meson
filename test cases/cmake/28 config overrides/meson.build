project('cmakeSubTest', ['c', 'cpp'])

cm = import('cmake')
sub_pro = cm.subproject('cmMod')

# TODO: In meson, CMake add_dependency does not work with all targets
# Ensure that all targets are built
tgt_internal = sub_pro.target('cmModLib_internal')
tgt_test_cmake = sub_pro.target('test_cmake')

# use the library through a config file w/ IMPORTED_LOCATION
sub_config = sub_pro.dependency('cmModLib++')
exe1 = executable('main1', ['main.cpp'], dependencies: [sub_config],
  link_depends: [tgt_internal, tgt_test_cmake])

# use the library through a config file w/ INTERFACE_LINK_LIBRARIES
sub2_config = sub_pro.dependency('cmModLib2', include_type: 'system')
exe2 = executable('main2', ['main.cpp'], dependencies: [sub2_config],
  link_depends: [tgt_internal, tgt_test_cmake])

test('test1', exe1)
test('test2', exe2)
