project('gtest', 'cxx')

gtest = find_dep('gtest', required : true)

e = executable('testprog', 'test.cc', deps : gtest)
add_test('gtest test', e)
