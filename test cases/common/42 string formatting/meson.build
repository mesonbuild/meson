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

templ2 = '@0@'
subs2 = '42'

if templ2.format(subs2) != '42'
  error('String formatting with variables is broken.')
endif

long = 'abcde'
prefix = 'abc'
suffix = 'cde'

if not long.startswith(prefix)
  error('Prefix.')
endif

if long.startswith(suffix)
  error('Not prefix.')
endif

if not long.endswith(suffix)
  error('Suffix.')
endif

if long.endswith(prefix)
  error('Not suffix.')
endif

if not long.contains(prefix)
  error('Does not contain prefix')
endif

if not long.contains(suffix)
  error('Does not contain suffix')
endif

if not long.contains('bcd')
  error('Does not contain middle part')
endif

if long.contains('dc')
  error('Broken contains')
endif

if long.to_upper() != 'ABCDE'
  error('Broken to_upper')
endif

if long.to_upper().to_lower() != long
  error('Broken to_lower')
endif

if 'struct stat.st_foo'.underscorify() != 'struct_stat_st_foo'
  error('Broken underscorify')
endif

if '#include <foo/bar.h>'.underscorify() != '_include__foo_bar_h_'
  error('Broken underscorify')
endif

# case should not change, space should be replaced, numbers are ok too
if 'Do SomeThing 09'.underscorify() != 'Do_SomeThing_09'
  error('Broken underscorify')
endif

assert('3'.to_int() == 3, 'String int conversion does not work.')
