project('test include path', 'c')

if meson.get_compiler('c').get_id() not in ['gcc', 'clang']
  error('MESON_SKIP_TEST: test needs #include_next <>')
endif

add_global_arguments('-iquote', meson.current_source_dir() / 'include', language: ['c'])

e = executable('executable', 'test.c', native: true)
test('executable', e)

subproject('hostsub')

# run the same test in a build-side subproject.  Even if that subproject
# uses "native: false", it has to use the build-side global arguments
# because nothing else would make sense in a cross compilation scenario.
subproject('buildsub', native: true)
