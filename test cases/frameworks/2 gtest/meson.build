project('gtest', 'cxx')

gtest = find_dep('gtest')

e = executable('testprog', 'test.cc', deps : gtest)
test('gtest test', e)
