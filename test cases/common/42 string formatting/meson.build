project('string formatting', 'c')

templ = '@0@bar@1@'

assert(templ.format('foo', 'baz') == 'foobarbaz', 'Basic string formatting is broken.')

assert('@0@'.format(1) == '1', 'String number formatting is broken.')

assert('@0@'.format(true) == 'true', 'String boolean formatting is broken.')

templ2 = '@0@'
subs2 = '42'

assert(templ2.format(subs2) == '42', 'String formatting with variables is broken.')

long = 'abcde'
prefix = 'abc'
suffix = 'cde'

assert(long.startswith(prefix), 'Prefix.')

assert(not long.startswith(suffix), 'Not prefix.')

assert(long.endswith(suffix), 'Suffix.')

assert(not long.endswith(prefix), 'Not suffix.')

assert(long.contains(prefix), 'Does not contain prefix')

assert(long.contains(suffix), 'Does not contain suffix')

assert(long.contains('bcd'), 'Does not contain middle part')

assert(not long.contains('dc'), 'Broken contains')

assert(long.to_upper() == 'ABCDE', 'Broken to_upper')

assert(long.to_upper().to_lower() == long, 'Broken to_lower')

assert('struct stat.st_foo'.underscorify() == 'struct_stat_st_foo', 'Broken underscorify')

assert('#include <foo/bar.h>'.underscorify() == '_include__foo_bar_h_', 'Broken underscorify')

# case should not change, space should be replaced, numbers are ok too
assert('Do SomeThing 09'.underscorify() == 'Do_SomeThing_09', 'Broken underscorify')

assert('3'.to_int() == 3, 'String int conversion does not work.')

assert(true.to_string() == 'true', 'bool string conversion failed')
assert(false.to_string() == 'false', 'bool string conversion failed')
assert(true.to_string('yes', 'no') == 'yes', 'bool string conversion with args failed')
assert(false.to_string('yes', 'no') == 'no', 'bool string conversion with args failed')
assert('@0@'.format(true) == 'true', 'bool string formatting failed')
