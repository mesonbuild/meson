creator = find_program('gen.py')

gen = generator(creator,
  output: '@BASENAME@.h',
  arguments : ['@INPUT@', '@OUTPUT@'])

res12 = gen.process('res1.txt', 'res2.txt')
