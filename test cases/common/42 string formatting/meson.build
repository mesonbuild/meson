project('string formatting', 'c')

templ = '@0@bar@1@'

if templ.format('foo', 'baz') != 'foobarbaz'
  error('Basic string formatting is broken.')
endif

if '@0@'.format(1) != '1'
  error('String number formatting is broken.')
endif

if '@0@'.format(true) != 'true'
  error('String boolean formatting is broken.')
endif
