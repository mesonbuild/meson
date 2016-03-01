project('postconf script', 'c')

meson.add_postconf_script('postconf.py', args: ['5', '33'])

test('post', executable('prog', 'prog.c'))
