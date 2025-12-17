project('declare dependency', 'c')

subdir('entity')

exe = executable('dep_user', 'main.c',
  dependencies : entity_dep)
test('dep', exe)

# just to make sure [] works as a no-op dep here
executable('dummy', 'main.c',
  dependencies : [entity_dep, []])

testcase expect_error('declare_dependency keyword argument \'link_with\' was of type array[InternalDependency] but should have been array[BothLibraries | SharedLibrary | StaticLibrary | CustomTarget | CustomTargetIndex | Jar | Executable]. Dependency and external_library objects must go in the "dependencies" keyword argument')
  declare_dependency(link_with : entity_dep)
endtestcase

testcase expect_error('declare_dependency keyword argument \'link_whole\' was of type array[InternalDependency] but should have been array[BothLibraries | StaticLibrary | CustomTarget | CustomTargetIndex]. Dependency and external_library objects must go in the "dependencies" keyword argument')
  declare_dependency(link_whole : entity_dep)
endtestcase

# simple case
declare_dependency(dependencies : entity_dep)

# nested deps should be flattened
declare_dependency(dependencies : [entity_dep])
declare_dependency(dependencies : [[entity_dep]])

# check that [] properly works as a no-op dep in declare_dependency() too
declare_dependency(dependencies : [])
declare_dependency(dependencies : [[]])
declare_dependency(dependencies : [entity_dep, []])
declare_dependency(dependencies : [[], entity_dep])
