project('generatorcustom', 'c')

if meson.get_compiler('c').get_id() != 'msvc'
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

  executable('proggie', 'main.c', allinone)
else
  error('MESON_SKIP_TEST: Skipping test on VS backend; see: https://github.com/mesonbuild/meson/issues/1004')
endif
