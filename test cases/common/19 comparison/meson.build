project('comparison', 'c')

var1 = 'foo'
var2 = 'bar'

if var1 == var2
  exe1 = executable('broken', 'broken.c')
else
  exe1 = executable('prog1', 'prog.c')
endif

if var1 == var1
  exe2 = executable('prog2', 'prog.c')
else
  exe2 = executable('broken', 'broken.c')
endif

if var1 != var2
  exe3 = executable('prog3', 'prog.c')
else
  exe3 = executable('broken', 'broken.c')
endif

if var1 != var1
  exe4 = executable('broken', 'broken.c')
else
  exe4 = executable('prog4', 'prog.c')
endif

test('equalfalse', exe1)
test('equaltrue', exe2)
test('nequaltrue', exe3)
test('nequalfalse', exe4)
