project('xorg format_man', version : '1.0.0')

xorg = import('unstable-xorg')

# TODO: test will fail on sysv systems

out = xorg.format_man('page.man', 'app')

test('test', find_program('test.py'), args : [out])
