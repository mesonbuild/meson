project('gmock test', 'cxx')

# Using gmock without gtest is a pain so just
# don't support that then.

gtest = find_dep('gtest', required : true)
gmock = find_dep('gmock', required : true)

e = executable('gmocktest', 'gmocktest.cc', deps : [gtest, gmock])
add_test('gmock test', e)
