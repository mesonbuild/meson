project('D Dub dependency test', 'd')

gtd = find_program('girtod', required: false)
if not gtd.found()
    error('MESON_SKIP_TEST: GirToD is not installed, so we can not run this test.')
endif

dlang = import('dlang')
glib_dep = dependency('glib-2.0')

gir_dep = dlang.gir_to_d('contrib/girwrap/')

e = executable('app', ['app.d'], dependencies: [gir_dep, glib_dep])
test('apptest', e)
