project('can-this-find-an-external-library', 'c')

cc = meson.get_compiler('c')

if cc.get_argument_syntax() != 'msvc'
  error('MESON_SKIP_TEST: test is only relevant for msvc and clang-cl')
endif

# We need to conjure a static library for the current architecture
# Generate an object file manually.
run_command(
  [
    meson.get_compiler('c').cmd_array().get(-1),
    '/nologo',
    '/MDd',
    '/Fo@0@'.format(meson.current_source_dir() / 'lib' / 'source.obj'),
    '/c',
    files('source.c'),
  ],
  check: true
)
# Turn it into a library.
run_command(
  [
    find_program('LIB'),
    '/OUT:@0@'.format(meson.current_source_dir() / 'lib' / 'conjured.lib'),
    meson.current_source_dir() / 'lib' / 'source.obj',
  ],
  check: true
)

# Ensure this library can be found
dep = cc.find_library('conjured', required: true)
