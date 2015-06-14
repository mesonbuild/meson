project('gtest', 'cpp')

gtest = dependency('gtest', main : true)
gtest_nomain = dependency('gtest', main : false)

e = executable('testprog', 'test.cc', dependencies : gtest)
test('gtest test', e)

e = executable('testprog_nomain', 'test_nomain.cc', dependencies : gtest_nomain)
test('gtest nomain test', e)
