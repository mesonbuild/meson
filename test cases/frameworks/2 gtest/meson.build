project('gtest', 'cpp')

gtest = dependency('gtest', main : true)

e = executable('testprog', 'test.cc', dependencies : gtest)
test('gtest test', e)
