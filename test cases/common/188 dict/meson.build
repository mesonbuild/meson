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

# Test keys() works as expected (note that it sorts the keys)
assert(dict.keys() == ['baz', 'foo', 'foo bar'], 'Keys returned unexpected list')

# Test values() works as expected (note that it sorts first, to match keys())
assert(dict.values() == ['foo', 'bar', 'baz'])

empty_dict = {}

foreach key, value : empty_dict
  assert(false, 'This dict should be empty')
endforeach

# Test keys() returns an empty list
assert(empty_dict.keys() == [], 'Keys for an empty dict should be an empty list')

# Test values() returns an empty list
assert(empty_dict.values() == [], 'Values for an empty dict should be an empty list')

d1 = empty_dict + {'a' : 'b'}
assert(d1 == {'a' : 'b'}, 'dict addition is not working')

d2 = d1 + {'a' : 'b2', 'c' : 'd'}
assert(d2 == {'a' : 'b2', 'c' : 'd'}, 'dict addition is not working')
assert(d1 == {'a' : 'b'}, 'dict should be immutable')

d3 = d2
d3 += {'e' : 'f'}
assert(d3 == {'a' : 'b2', 'c' : 'd', 'e' : 'f'}, 'dict plusassign is not working')
assert(d2 == {'a' : 'b2', 'c' : 'd'}, 'dict should be immutable')

dict1 = {}

# A variable to be used as a key
testkey1 = 'myKey1'
testkey2 = 'myKey2'

# Add new entry using the variable
dict1 += {testkey1 : 'myValue'}
dict1 += {testkey2 : 42}

# Test that the stored values are correct
assert(dict1[testkey1] == 'myValue',
       'Incorrect string value retrieved from dictionary - variable key')
assert(dict1['myKey1'] == 'myValue',
       'Incorrect string value retrieved from dictionary - literal key')
assert(dict1[testkey2] == 42,
       'Incorrect int value retrieved from dictionary - variable key')
assert(dict1['myKey2'] == 42,
       'Incorrect int value retrieved from dictionary - literal key')

d = {testkey1 : 1}
assert(d[testkey1] == 1,
       'Incorrect int value retrieved from dictionary - variable key')
assert(d['myKey1'] == 1,
       'Incorrect int value retrieved from dictionary - literal key')

d = {'1' / '2' : 1, join_paths('a', 'b') : 2}
k1 = '1' / '2'
k2 = join_paths('a', 'b')
assert(d[k1] == 1, 'Incorrect expression evaluation in dictionary key')
assert(d[k2] == 2, 'Incorrect expression evaluation in dictionary key')

d = {'a' + 'b' : 1}
assert(d['a' + 'b'] == 1, 'Incorrect expression evaluation in dictionary key')
assert(d['ab'] == 1, 'Incorrect expression evaluation in dictionary key')

# Complex types
d = {
  'sanity': 1,
  'host': host_machine,
  'meson': meson,
}

assert(d['sanity'] == 1)
assert(not is_disabler(d['meson']))
assert(not is_disabler(d['host']))
