project('foobar', 'c')

if meson.get_compiler('c').get_id() == 'gcc' and host_machine.system() == 'windows'
    error('MESON_SKIP_TEST windres has internal error when adding . to include path')
endif

win = import('windows')

subdir('a')
subdir('b')
subdir('c')
subdir('exe3')
subdir('exe4')

main = win.compile_resources('rsrc.rc')

testa = executable('testa', 'verify.c', a)
testb = executable('testb', 'verify.c', b)
testc = executable('testc', 'verify.c', c)
testmain = executable('testmain', 'verify.c', main)

test('a', testa, args: 'a')
test('b', testb, args: 'b')
test('c', testc, args: 'c')
test('main', testmain, args: 'main')
