project('generator depend files', 'c')

copy = find_program('copyfile.py')

gen = generator(copy,
  output    : ['@BASENAME@'],
  arguments : ['@INPUT@', '@OUTPUT@'],
  depend_files : 'dep.dat'
)

foo_src = gen.process('foo.c.in')

executable('foo', foo_src)
