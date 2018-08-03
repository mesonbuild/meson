project('dict test', 'c')

dict = {'foo' : 'bar',
        'baz' : 'foo',
        'foo bar': 'baz'}

exe = executable('prog', sources : ['prog.c'])

i = 0

foreach key, value : dict
  test('dict test @0@'.format(key), exe,
    args : [dict[key], value])
  i += 1
endforeach

assert(i == 3, 'There should be three elements in that dictionary')

empty_dict = {}

foreach key, value : empty_dict
  assert(false, 'This dict should be empty')
endforeach
