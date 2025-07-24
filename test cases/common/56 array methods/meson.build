project('array methods', meson_version : '>= 1.9')

empty = []
one = ['abc']
two = ['def', 'ghi']
combined = [empty, one, two]

file_list = files('a.txt', 'b.txt')
file_a = files('a.txt')
file_c = files('c.txt')

if file_a[0] != file_list[0]
  error('Files are not equal')
endif

if not file_list.contains(file_a[0])
  error('Contains with ObjectHolder lists does not work')
endif

if file_list.contains(file_c[0])
  error('Contains with ObjectHolder lists found nonexistent object')
endif

if empty.contains('abc')
  error('Empty is not empty.')
endif

if one.contains('a')
  error('One claims to contain a')
endif

if not one.contains('abc')
  error('One claims to not contain abc.')
endif

if one.contains('abcd')
  error('One claims to contain abcd.')
endif

if two.contains('abc')
  error('Two claims to contain abc.')
endif

if not two.contains('def')
  error('Two claims not to contain def.')
endif

if not two.contains('ghi')
  error('Two claims not to contain ghi.')
endif

if two.contains('defg')
  error('Two claims to contain defg.')
endif

if not combined.contains('abc')
  error('Combined claims not to contain abc.')
endif

if not combined.contains(one)
  error('Combined claims not to contain [abc].')
endif

if not combined.contains(two)
  error('Combined claims not to contain [def, ghi].')
endif

if not combined.contains('ghi')
  error('Combined claims not to contain ghi.')
endif

# test array slicing
assert(['a', 'b', 'c'].slice() == ['a', 'b', 'c'])
assert(['a', 'b', 'c'].slice(step : 2) == ['a', 'c'])
assert(['a', 'b', 'c'].slice(step : -1) == ['c', 'b', 'a'])
assert(['a', 'b', 'c'].slice(step : -2) == ['c', 'a'])
assert(['a', 'b', 'c'].slice(1, 2) == ['b'])
assert(['a', 'b', 'c'].slice(2, -2) == [])
assert(['a', 'b', 'c'].slice(-9876543, 2) == ['a', 'b'])
assert(['a', 'b', 'c', 'd', 'e'].slice(1, 12, step : 2) == ['b', 'd'])

# test array flattening
x = ['a', ['b'], [[[[[[['c'], 'd']]], 'e']]]]
assert(x.length() == 3)
assert(x.flatten().length() == 5)
assert(x.flatten() == ['a', 'b', 'c', 'd', 'e'])
assert(['a', ['b', 'c']].flatten() == ['a', 'b', 'c'])
