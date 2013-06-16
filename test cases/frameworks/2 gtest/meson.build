project('gtest', 'cpp')

gtest = dependency('gtest', main : true)

e = executable('testprog', 'test.cc', deps : gtest)
test('gtest test', e)
