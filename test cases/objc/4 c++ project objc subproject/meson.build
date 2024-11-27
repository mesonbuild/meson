project('master', ['cpp'])

if get_option('backend').startswith('vs')
  error('MESON_SKIP_TEST: objc is not supported by vs backend')
endif

foo = subproject('foo')
dep = foo.get_variable('foo_dep')

executable('master', 'master.cpp', dependencies: dep)
