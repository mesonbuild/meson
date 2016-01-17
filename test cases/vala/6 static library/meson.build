project('valastatic', 'vala', 'c')

valadeps = [dependency('glib-2.0'), dependency('gobject-2.0')]

l = static_library('valalib', 'mylib.vala', dependencies : valadeps)

e = executable('valaprog', 'prog.vala',
link_with : l,
dependencies : valadeps)

test('valastatictest', e)
