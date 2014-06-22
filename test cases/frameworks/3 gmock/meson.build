project('gmock test', 'cpp')

# Using gmock without gtest is a pain so just
# don't support that then.

gtest = dependency('gtest', main : true)
gmock = dependency('gmock')

e = executable('gmocktest', 'gmocktest.cc', dependencies : [gtest, gmock])
test('gmock test', e)
