project('all sources generated', 'cpp')

comp = find_program('converter.py')

c = custom_target('outputfile',
  input : 'foobar.c.in',
  output : 'foobar.cpp',
  command : [comp, '@INPUT@', '@OUTPUT@'],
)

prog = executable('genexe', c)
