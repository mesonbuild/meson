project('generatorcustom', 'c')

creator = find_program('gen.py')
catter = find_program('catter.py')
gen_resx = find_program('gen-resx.py')

gen = generator(creator,
  output: '@BASENAME@.h',
  arguments : ['@INPUT@', '@OUTPUT@'])

res3 = custom_target('gen-res3',
    output : 'res3.txt',
    command : [gen_resx, '@OUTPUT@', '3'])

res4 = custom_target('gen-res4',
    output : 'res4.txt',
    command : [gen_resx, '@OUTPUT@', '4'])

hs = gen.process('res1.txt', 'res2.txt', res3, res4[0])

allinone = custom_target('alltogether',
    input : hs,
    output : 'alltogether.h',
    command : [catter, '@INPUT@', '@OUTPUT@'])

proggie = executable('proggie', 'main.c', allinone)

test('proggie', proggie)
