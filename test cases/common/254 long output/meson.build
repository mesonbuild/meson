project('long-stderr', 'c')

dumper = executable('dumper', 'dumper.c')
test('dump-test', dumper, timeout: 120)
test('dump-test-TAP', dumper, protocol : 'tap', timeout: 120)
