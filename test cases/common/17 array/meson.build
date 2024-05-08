project('array test', 'c')

arr = [
  'func.c',
  'prog.c']

exe = executable('prog', sources : arr)
test('arr test', exe)


# Array arithmetic

array1 = ['foo', 'bar']
array2 = ['qux', 'baz']

if array1 + array2 != ['foo', 'bar', 'qux', 'baz']
  error('Array concatenation is broken')
endif
if array2 + array1 != ['qux', 'baz', 'foo', 'bar']
  error('Array concatenation is broken')
endif

if array1 + array1 + array1 != ['foo', 'bar', 'foo', 'bar', 'foo', 'bar']
  error('Many-array concatenation is broken')
endif


# Array methods

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

if file_list.unique(file_a) != file_list
  error('File not deduplicated in list')
endif

if empty.unique(one, two) != one + two
  error('Unique does not combine arrays')
endif

if [0, 0, 0, 1, 1, 2, 3, 2, 1, 4, 0, 5].unique() != [0, 1, 2, 3, 4, 5]
  error('Unique without arguments did not deduplicated integers')
endif
