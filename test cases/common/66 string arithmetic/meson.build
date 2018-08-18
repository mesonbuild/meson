project('string arithmetic', 'c')

if 'foo' + 'bar' != 'foobar'
  error('String concatenation is broken')
endif

if 'foo' + 'bar' + 'baz' != 'foobarbaz'
  error('Many-string concatenation is broken')
endif

a = 'a'
b = 'b'

if a + b + 'c' != 'abc'
  error('String concat with variables is broken.')
endif
