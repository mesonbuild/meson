project('test default_options in find_program')

dummy_exe = find_program('dummy', default_options: ['subproject_option=true'])

test('test_dummy', dummy_exe)

# Test that a suproject that fails does not alter global state, specifically if
# A => B, where B alters that state, but A fails after successfully configuring B
subproject('will_fail', required : false)

p = find_program('python', 'python3')
assert(p.version().version_compare('< 1000'), 'failed subproject altered global state')
