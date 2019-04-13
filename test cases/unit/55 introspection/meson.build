project('introspection', ['c', 'cpp'], version: '1.2.3', default_options: ['cpp_std=c++11', 'buildtype=debug'])

dep1 = dependency('threads')
dep2 = dependency('zlib', required: false)
dep3 = dependency('bugDep1', required: get_option('test_opt1'))

b1 = get_option('test_opt1')
b2 = get_option('test_opt2')
test_bool = b1 or b2
test_bool = b1 and b2

set_variable('list_test_plusassign', [])
list_test_plusassign += ['bugs everywhere']

if false
  dependency('somethingthatdoesnotexist', required: true)
  dependency('look_i_have_a_fallback', fallback: ['oh_no', 'the_subproject_does_not_exist'])
endif

subdir('sharedlib')
subdir('staticlib')

t1 = executable('test1', 't1.cpp', link_with: [sharedlib], install: true, build_by_default: get_option('test_opt2'))
t2 = executable('test2', 't2.cpp', link_with: [staticlib])
t3 = executable('test3', 't3.cpp', link_with: [sharedlib, staticlib], dependencies: [dep1])

test('test case 1', t1)
test('test case 2', t2)
benchmark('benchmark 1', t3)
