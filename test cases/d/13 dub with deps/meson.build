project('dub-example', 'd')

dub_exe = find_program('dub', required : false)
if not dub_exe.found()
  error('MESON_SKIP_TEST: Dub not found')
endif

vibed_http_dep = dependency('vibe-d:http', method: 'dub')

test_exe = executable('test-vibed', 'test.d', dependencies: vibed_http_dep)
test('test vibe-d', test_exe)
