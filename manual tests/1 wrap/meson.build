project('downloader', 'c')

s = subproject('sqlite')

libdl = find_library('dl', required : false)

e = executable('dtest', 'main.c',
  include_directories : s.get_variable('sqinc'),
  link_args : ['-pthread'],
  c_args : '-pthread',
  dependencies : libdl,
  link_with : s.get_variable('sqlib'))

test('dltest', e)
