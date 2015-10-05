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

if not is_variable('var1')
  error('Is_variable fail.')
endif

if is_variable('nonexisting')
  error('Is_variable fail 2.')
endif

if not get_variable('var1', false)
  error('Get_variable fail.')
endif

if get_variable('nonexisting', false)
  error('Get_variable fail.')
endif
