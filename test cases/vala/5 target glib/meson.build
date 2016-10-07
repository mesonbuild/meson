project('valatest', 'vala', 'c', default_options : ['werror=true'])

valadeps = [dependency('glib-2.0', version : '>=2.32'), dependency('gobject-2.0')]

e = executable('valaprog', 'GLib.Thread.vala', dependencies : valadeps)
test('valatest', e)
