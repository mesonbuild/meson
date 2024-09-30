project('objfw build tests', 'objc')

if get_option('backend').startswith('vs')
  error('MESON_SKIP_TEST: objc is not supported by vs backend')
endif

objfw_dep = dependency('objfw', required: false)
objfwtest_dep = dependency('objfw', modules: ['ObjFWTest'], required: false)

if not objfw_dep.found() or not objfwtest_dep.found()
  error('MESON_SKIP_TEST: Need objfw dependency')
endif

executable('TestApplication', 'TestApplication.m',
  dependencies: [objfw_dep])

executable('SimpleTest', 'SimpleTest.m',
  dependencies: [objfwtest_dep])
