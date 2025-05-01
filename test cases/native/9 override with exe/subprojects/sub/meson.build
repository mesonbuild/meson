project('sub', 'c', version : '1.0', meson_version: '>= 1.9.0')
foobar = executable('foobar', 'foobar.c',  native : true)
meson.override_find_program('foobar', foobar)

found_foobar = find_program('foobar')
if found_foobar.version() != meson.project_version()
  error('Overriden Executable had incorrect version: got @0@, expected @1@'.format(found_foobar.version(), meson.project_version()))
endif

test('foobar executable', foobar, args : [ meson.current_build_dir() / 'test-output.c' ])
test('overriden foobar executable', found_foobar, args : [ meson.current_build_dir() / 'test-output.c' ])
