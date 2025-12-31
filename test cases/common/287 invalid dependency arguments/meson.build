project('test', 'c')

testcase expect_error('executable keyword argument \'dependencies\' was of type array[SubprojectHolder] but should have been array[Dependency | InternalDependency]')
  executable('main', 'main.c', dependencies: subproject('sub'))
endtestcase

lib = static_library('lib', 'lib.c')

testcase expect_error('executable keyword argument \'dependencies\' was of type array[StaticLibrary] but should have been array[Dependency | InternalDependency]. Tried to use a build_target "lib" as a dependency. This should be in `link_with` or `link_whole` instead.')
  executable('main', 'main.c', dependencies : lib)
endtestcase
