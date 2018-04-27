project('dict test', 'c')

dict = {'foo' : 'bar',
        'baz' : 'foo',
        'foo bar': 'baz'}

exe = executable('prog', sources : ['prog.c'])

foreach key, value : dict
  test('dict test @0@'.format(key), exe,
    args : [dict[key], value])
endforeach
