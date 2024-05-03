project('test suite', meson_version: '>= 1.5.0')

py = find_program('python3')
args = ['-c', 'raise SystemExit(0)']

test_a = test('test A', py, args: args, suite: 'A')
test_b = test('test B', py, args: args, suite: ['A', 'B'])
test_c = test('test C', py, args: args)
bench_d = benchmark('bench D', py, args: args)

add_test_suite('all', test_a, test_b, test_c)
add_test_suite('everything', [test_a, [test_b], test_c], bench_d)
add_test_suite('A', test_a, test_c)
