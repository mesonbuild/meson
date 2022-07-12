project('long-stderr', 'c')

dumper = executable('dumper', 'dumper.c')
test('dump-test', dumper)
test('dump-test-TAP', dumper, protocol : 'tap')
