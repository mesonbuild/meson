project('array methods', 'c')

empty = []
one = ['abc']
two = ['def', 'ghi']
combined = [empty, one, two]

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

if not combined.contains('ghi')
  error('Combined claims not to contain ghi.')
endif
