# Catch2 3.3 or newer must be installed on the system.
project('catch2', 'cpp')

catch2 = dependency('catch2-with-main', version : '>=3.3.0', required : false)
if not catch2.found()
  error('MESON_SKIP_TEST: Catch2 3.3 or newer not installed.')
endif

e = executable('testprog', 'test.cpp', dependencies : catch2)
test('catch2 test', e, protocol : 'catch2')
