project('link_depends_indexed_custom_target', 'c')

if meson.backend().startswith('vs')
  # FIXME: Broken on the VS backends
  error('MESON_SKIP_TEST see https://github.com/mesonbuild/meson/issues/1799')
endif

cmd = find_program('make_file.py')

dep_files = custom_target('gen_dep',
        command: [cmd, '@OUTPUT@'],
        output: ['dep_file1', 'dep_file2'])

exe = executable('foo', 'foo.c',
        link_depends: dep_files[1],
        c_args: ['-DDEPFILE="' + dep_files[0].full_path()+ '"'])

# check that dep_file1 exists, which means that link_depends target ran
test('runtest', exe)
