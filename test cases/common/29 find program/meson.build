project('find program', 'c')

if build_machine.system() == 'windows'
  # Things Windows does not provide:
  #  - an executable to copy files without prompting
  #  - working command line quoting
  #  - anything that you might actually need
  # Because of these reasons we only check that
  # the program can be found.
  cp = find_program('xcopy')
else
  cp = find_program('donotfindme', 'cp')
  gen = generator(cp, \
   output  : '@BASENAME@.c', \
   arguments : ['@INPUT@', '@OUTPUT@'])

  generated = gen.process('source.in')
  e = executable('prog', generated)
  test('external exe', e)
endif
