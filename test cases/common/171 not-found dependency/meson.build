project('dep-test', 'c')

dep = dependency('', required:false)
if dep.found()
  error('not-found dependency was found')
endif

assert(dep.type_name() == 'not-found', 'dependency should be of type "not-found" not ' + dep.type_name())

library('testlib', 'testlib.c', dependencies: [dep])
subdir('sub', if_found: dep)
