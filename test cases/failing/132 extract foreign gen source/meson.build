project('extract foreign gen source', 'c')

gen = generator(
  find_program('create-source.py'),
  arguments: ['@INPUT@'],
  output: '@BASENAME@_gen.c',
  capture: true
)

gen_src = gen.process('main.c')

foo = library('foo', 'empty.c')

bar = executable('bar', foo.extract_objects(gen_src))
