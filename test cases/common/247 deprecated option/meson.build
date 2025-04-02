project('deprecated options',
  default_options: [
    'o1=false',
    'o2=a,b',
    'o3=a,b',
    'o4=true',
    'o5=auto',
    'o6=false',
    'o8=/foo',
    ':p1=false',
    ':p2=a,b',
    ':p3=a,b',
    ':p4=true',
    ':p5=auto',
    ':p6=false',
    ':p8=/foo',
  ]
)

assert(get_option('o1') == false)
assert(get_option('p1') == false)
assert(get_option('c1') == false)
assert(get_option('o2') == ['a', 'b'])
assert(get_option('p2') == ['a', 'b'])
assert(get_option('c2') == ['a', 'b'])
assert(get_option('o3') == ['c', 'b'])
assert(get_option('p3') == ['c', 'b'])
assert(get_option('c3') == ['c', 'b'])
assert(get_option('o4').enabled())
assert(get_option('p4').enabled())
assert(get_option('c4').enabled())
assert(get_option('o5') == false)
assert(get_option('p5') == false)
assert(get_option('c5') == false)
assert(get_option('o6') == false)
assert(get_option('p6') == false)
assert(get_option('c6') == false)
assert(get_option('o7').disabled())
assert(get_option('python.platlibdir') == '/foo')
