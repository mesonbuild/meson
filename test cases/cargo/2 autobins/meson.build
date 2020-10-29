project('basic cargo test', 'rust')

rust = import('unstable-rust')

# This implements the 2018 behavior, when no manual bins are defined
sub = rust.subproject('test')
app = sub.get_variable('app')
tester = find_program('test.py')
test('test 2018 behavior (no manual)', tester, args : [app])

# test the 2018 behavior, which autobins default to true, even if manual bins
# are defined
subp = rust.subproject('sub2')
app = subp.get_variable('app')
test('test 2018 behavior (manual)', app)

# this implements the 2015 behavior, when no bins are defined
subp = rust.subproject('sub')
app = subp.get_variable('app')
test('test 2015 behavior (no manual)', app)

# test the 2015 behavior, which autobins default to false if any manual bins
# are defined.
subp = rust.subproject('sub3')
app = subp.get_variable('app', 'sentinal')
assert(app == 'sentinal', 'autobins should not be on')
