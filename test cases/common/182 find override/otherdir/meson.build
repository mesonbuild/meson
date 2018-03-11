gen = find_program('codegen') # Should use overridden value set in "subdir".

src = custom_target('arrival',
  input : 'source.desc',
  output : 'file.c',
  command : [gen, '@INPUT@', '@OUTPUT@']
  )

e = executable('six', 'main.c', src)

test('six', e)
