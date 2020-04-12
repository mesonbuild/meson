gensrc = generator(output: ['@BASENAME@.h', '@BASENAME@.c'],
  command: [find_program('gensrc.py'), '@INPUT@', '@OUTPUT0@', '@OUTPUT1@']
)

compsrc = generator_target('generate',
  sources: xmlloc,
  generator: gensrc)
