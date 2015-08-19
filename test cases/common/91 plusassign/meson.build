project('plusassign', 'c')

x = []

x += 'a'

if x.length() != 1
  error('Incorrect append')
endif

if x[0] != 'a'
  error('Incorrect append 2.')
endif

y = x

x += 'b'

if y.length() != 1
  error('Immutability broken.')
endif

if y[0] != 'a'
  error('Immutability broken 2.')
endif

if x.length() != 2
  error('Incorrect append 3')
endif

if x[0] != 'a'
  error('Incorrect append 4.')
endif

if x[1] != 'b'
  error('Incorrect append 5.')
endif

# Now with evil added: append yourself.

x += x

if x.length() != 4
  error('Incorrect selfappend.')
endif
