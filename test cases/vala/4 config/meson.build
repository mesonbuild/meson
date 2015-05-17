project('valatest', 'vala', 'c')

valadeps = [dependency('glib-2.0'), dependency('gobject-2.0')]

e = executable(
'valaprog',
sources : ['config.vapi', 'prog.vala'],
dependencies : valadeps,
c_args : '-DDATA_DIRECTORY="@0@"'.format(meson.current_source_dir())
)
test('valatest', e)
