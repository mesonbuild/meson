project('if test', 'c')

var1 = true
set_variable('var2', false)

if var1
  exe = executable('prog', 'prog.c')
endif

if var2
  exe = executable('breakbreakbreak', 'crashing.c')
endif

test('iftest', exe)
