project('shared library', 'vala', 'c', meson_version : '>= 1.11.0')

valadeps = [dependency('glib-2.0'), dependency('gobject-2.0')]

libinc = include_directories('lib')

subdir('lib')
subdir('prog')

test('valasharedtest', e)
