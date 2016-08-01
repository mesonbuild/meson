project('ternary operator', 'c')

one = true ? 1 : error('False branch should not be evaluated')
two = false ? error('True branch should not be evaluated.') : 2

assert(one == 1, 'Return value from ternary true is wrong.')
assert(two == 2, 'Return value from ternary false is wrong.')
