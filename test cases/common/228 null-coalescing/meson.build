project('null-coalescing', 'c')

one = true ?? 'no'
two = false ?? 'yes'
three = '@0@'.format(true ?? 'yes')
four = '@0@'.format(false ?? 'no')
five = [true ?? '0']
six = [false ?? '1']

assert(one == true, 'Return value from null-coalescing true is wrong.')
assert(two == 'yes', 'Return value from null-coalescing false is wrong.')
assert(three == 'true', 'Return value from null-coalescing true inside method is wrong.')
assert(four == 'no', 'Return value from null-coalescing false inside method is wrong.')
assert(five == [true], 'Return value for null-coalescing true inside of list is wrong.')
assert(six == ['1'], 'Return value for null-coalescing false inside of list is wrong.')
