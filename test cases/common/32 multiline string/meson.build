project('multiline string', 'c')

x = '''hello again'''
y = '''hello
again'''

if x == y
  error('Things are wrong.')
endif

multieol = '''
'''
singleeol = '\n'

if multieol != singleeol
  error('Newline quoting is broken.')
endif

# And one more for good measure.
quote1 = ''' ' '''.strip()
quote2 = '\''

if quote1 != quote2
  error('Single quote quoting is broken.')
endif
