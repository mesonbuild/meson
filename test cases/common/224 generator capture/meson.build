project('generator', 'c')

cat = find_program('cat.py')
generator = generator(cat,
  arguments : [ '@INPUT@', '@OUTPUT@' ],
  output : '@BASENAME@',
  capture : true,
)

executable('exec', generator.process('source.c.txt'))
