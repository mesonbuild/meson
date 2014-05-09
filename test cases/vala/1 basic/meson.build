project('valatest', 'vala', 'c')

valadeps = [dependency('glib-2.0'), dependency('gobject-2.0')]

e = executable('valaprog', 'prog.vala', deps : valadeps)
test('valatest', e)
