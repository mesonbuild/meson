project('foobar', 'c')

win = import('windows')

subdir('a')
subdir('b')
subdir('c')

main = win.compile_resources('rsrc.rc')

testa = executable('testa', 'verify.c', a)
testb = executable('testb', 'verify.c', b)
testc = executable('testc', 'verify.c', c)
testmain = executable('testmain', 'verify.c', main)

test('a', testa, args: 'a')
test('b', testb, args: 'b')
test('c', testc, args: 'c')
test('main', testmain, args: 'main')
