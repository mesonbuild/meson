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

d1 = empty_dict + {'a' : 'b'}
assert(d1 == {'a' : 'b'}, 'dict addition is not working')

d2 = d1 + {'a' : 'b2', 'c' : 'd'}
assert(d2 == {'a' : 'b2', 'c' : 'd'}, 'dict addition is not working')
assert(d1 == {'a' : 'b'}, 'dict should be immutable')

d3 = d2
d3 += {'e' : 'f'}
assert(d3 == {'a' : 'b2', 'c' : 'd', 'e' : 'f'}, 'dict plusassign is not working')
assert(d2 == {'a' : 'b2', 'c' : 'd'}, 'dict should be immutable')
