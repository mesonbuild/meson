project('sub', 'c', version : '1.0')
foobar = executable('foobar', 'foobar.c',  native : true)
meson.override_find_program('foobar', foobar)

# Force this to be used for the host machine.
meson.override_find_program('foobar2', foobar, native : false)
