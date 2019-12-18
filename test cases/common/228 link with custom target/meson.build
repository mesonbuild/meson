project('link with custom targets', 'c')
t = custom_target('dummy', output: [ 'libdummy.a' ], command: [ 'echo', 'dummy' ])
dep1 = declare_dependency(link_with: t)
dep2 = declare_dependency(link_with: t[0])

static_library('lib1', 'empty.c', dependencies: dep1, install: true)
static_library('lib2', 'empty.c', dependencies: dep2, install: true)
