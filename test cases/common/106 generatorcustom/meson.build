project('generatorcustom', 'c')

creator = find_program('gen.py')
catter = find_program('catter.py')

gen = generator(creator,
  output: '@BASENAME@.h',
  arguments : ['@INPUT@', '@OUTPUT@'])

hs = gen.process('res1.txt', 'res2.txt')

allinone = custom_target('alltogether',
    input : hs,
    output : 'alltogether.h',
    command : [catter, '@INPUT@', '@OUTPUT@'])

proggie = executable('proggie', 'main.c', allinone)

test('proggie', proggie)

