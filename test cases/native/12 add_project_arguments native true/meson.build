project('test include path', 'c')

if meson.get_compiler('c').get_id() not in ['gcc', 'clang']
  error('MESON_SKIP_TEST: test needs #include_next <>')
endif

add_project_arguments('-iquote', meson.current_source_dir() / 'include', language: ['c'])

e = executable('executable', 'test.c', native: true)
test('executable', e)
