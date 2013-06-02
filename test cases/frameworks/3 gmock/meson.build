project('gmock test', 'cxx')

# Using gmock without gtest is a pain so just
# don't support that then.

gtest = find_dep('gtest')
gmock = find_dep('gmock')

e = executable('gmocktest', 'gmocktest.cc', deps : [gtest, gmock])
test('gmock test', e)
