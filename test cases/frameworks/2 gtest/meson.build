project('gtest', 'cxx')

gtest = find_dep('gtest')

e = executable('testprog', 'test.cc', deps : gtest)
add_test('gtest test', e)
