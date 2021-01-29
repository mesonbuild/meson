project('dub-example', 'd')

dub_exe = find_program('dub', required : false)
if not dub_exe.found()
  error('MESON_SKIP_TEST: Dub not found')
endif

test3_dep = dependency('dubtestproject:test3', method: 'dub')

test_exe = executable('test3', 'dummy.d', dependencies: test3_dep)
test('test test3', test_exe)
