project('test features', 'c')

tester = executable('tester', 'tester.c')
test('nonzero return code', tester, args : [], protocol: 'tap')
test('missing test', tester, args : ['1..1'], protocol: 'tap')
test('incorrect skip', tester, args : ['1..1 # skip\nok 1'], protocol: 'tap')
