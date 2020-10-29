project('basic cargo test', 'rust')

rust = import('unstable-rust')
sub = rust.subproject('test')

app = sub.get_variable('app')

# Test a source != name
printer = sub.get_variable('printer')

tester = find_program('test.py')

test('test', tester, args : [app, 'Hello World!'])
test('test', printer, args : [app, 'This is an app!'])
