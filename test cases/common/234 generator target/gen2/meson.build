g2 = generator(  output: '@BASENAME@.xlc',
  command: [find_program('localizexml.py'), '@INPUT@', '@OUTPUT@']
)

xmlloc = generator_target('localize',
  xml1,
  generator: g2
)
