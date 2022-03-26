project('dub-with-deps-example', ['d'])

dub_exe = find_program('dub', required : false)
if not dub_exe.found()
    error('MESON_SKIP_TEST: Dub not found')
endif

if meson.get_compiler('d').get_id() == 'gcc'
    error('MESON_SKIP_TEST: can\'t build dependencies with GDC')
endif

xlsx_dep = dependency('xlsx', method: 'dub')

test_exe = executable('test-test6', 'test.d', dependencies: xlsx_dep)

test('test dub with deps', test_exe)
