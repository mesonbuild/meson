project('dep fallback', 'c')

bob = dependency('boblib', fallback : ['boblib', 'bob_dep'], required: false)
if not bob.found()
    error('Bob is actually needed')
endif
jimmy = dependency('jimmylib', fallback : ['jimmylib', 'jimmy_dep'], required: false)

gensrc_py = find_program('gensrc.py')
gensrc = custom_target('gensrc.c',
  input : 'tester.c',
  output : 'gensrc.c',
  command : [gensrc_py, '@INPUT@', '@OUTPUT@'])

exe = executable('bobtester',
  [gensrc],
  dependencies : bob)

test('bobtester', exe)
