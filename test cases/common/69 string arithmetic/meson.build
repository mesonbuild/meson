project('string arithmetic', 'c')

if 'foo' + 'bar' != 'foobar'
  error('String concatenation is broken')
endif

if 'foo' + 'bar' + 'baz' != 'foobarbaz'
  error('Many-string concatenation is broken')
endif

if 'foobar' + 5 != 'foobar5' or 5 + 'foobar' != '5foobar'
  error('String-number concatenation is broken')
endif

if (5 + 3) + 'foobar' != '8foobar'
  error('String-number addition then concatenation broken')
endif
if 5 + (3 + 'foobar') != '53foobar'
  error('String-number concatenation then addition broken')
endif
