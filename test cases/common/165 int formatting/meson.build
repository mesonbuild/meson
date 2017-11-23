project('int formatting', 'c')

values = [
  ['', '74'],
  ['c', 'J'],
  ['b', '1001010'],
  ['d', '74'],
  ['o', '112'],
  ['x', '4a'],
  ['X', '4A']
]

foreach value: values
  assert(74.to_string(value[0]) == value[1], 'conversion is broken')
endforeach
