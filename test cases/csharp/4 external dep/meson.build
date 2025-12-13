project('C# external library', 'cs')
glib_sharp_3 = dependency('glib-sharp-3.0', required : false)

if not glib_sharp_3.found()
  error('MESON_SKIP_TEST glib# not found.')
endif

e = executable('prog', 'prog.cs', dependencies: glib_sharp_3, install : true)
test('libtest', e, args: [join_paths(meson.current_source_dir(), 'hello.txt')])
