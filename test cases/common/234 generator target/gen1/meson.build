g1 = generator(find_program('comp2xml.py'),
  output: '@BASENAME@.xc',
  arguments: ['@INPUT@', '@OUTPUT@'],
)

xml1 = generator_target('gen1',
  input: ['first.component',
          'second.component',
          'third.component',
         ],
  generator: g1
)
