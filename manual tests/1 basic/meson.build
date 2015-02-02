project('downloader', 'c')

s = subproject('sqlite')

e = executable('dtest', 'main.c',
include_directories : s.get_variable('sqinc'),
link_args : ['-pthread', '-ldl'],
c_args : '-pthread',
link_with : s.get_variable('sqlib'))

test('dltest', e)
