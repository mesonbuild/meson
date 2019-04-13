project('test env var stacking')

testenv = environment()
testenv.set('TEST_VAR_SET', 'some-value')
testenv.set('TEST_VAR_APPEND', 'some-value')
testenv.set('TEST_VAR_PREPEND', 'some-value')

testenv.append('TEST_VAR_APPEND', 'another-value-append', separator: ':')
testenv.prepend('TEST_VAR_PREPEND', 'another-value-prepend', separator: ':')
testenv.set('TEST_VAR_SET', 'another-value-set')

test('check env', find_program('script.py'), env: testenv)
