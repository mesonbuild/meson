project('comparison', 'c')

# Compare equality of strings

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

# Non-equality comparisons

var3 = 3
var4 = 4

if var3 < var4
  exe5 = executable('prog5', 'prog.c')
else
  exe5 = executable('broken', 'broken.c')
endif

if var3 < var3
  exe6 = executable('broken', 'broken.c')
else
  exe6 = executable('prog6', 'prog.c')
endif

if var4 > var3
  exe7 = executable('prog7', 'prog.c')
else
  exe7 = executable('broken', 'broken.c')
endif

if var3 > var3
  exe8 = executable('broken', 'broken.c')
else
  exe8 = executable('prog8', 'prog.c')
endif

if var4 <= var3
  exe9 = executable('broken', 'broken.c')
else
  exe9 = executable('prog9', 'prog.c')
endif

if var3 <= var3
  exe10 = executable('prog10', 'prog.c')
else
  exe10 = executable('broken', 'broken.c')
endif

if var3 >= var4
  exe11 = executable('broken', 'broken.c')
else
  exe11 = executable('prog11', 'prog.c')
endif

if var3 >= var3
  exe12 = executable('prog12', 'prog.c')
else
  exe12 = executable('broken', 'broken.c')
endif

test('lttrue', exe5)
test('ltfalse', exe6)
test('gttrue', exe7)
test('gtfalse', exe8)
test('lefalse', exe9)
test('letrue', exe10)
test('gefalse', exe11)
test('getrue', exe12)

# Non-elementary type comparisons

if exe1 == exe2
  exe13 = executable('broken', 'broken.c')
else
  exe13 = executable('prog13', 'prog.c')
endif

if exe1 == exe1
  exe14 = executable('prog14', 'prog.c')
else
  exe14 = executable('broken', 'broken.c')
endif

if exe1 != exe2
  exe15 = executable('prog15', 'prog.c')
else
  exe15 = executable('broken', 'broken.c')
endif

if exe1 != exe1
  exe16 = executable('broken', 'broken.c')
else
  exe16 = executable('prog16', 'prog.c')
endif

test('equalfalse', exe13)
test('equaltrue', exe14)
test('nequaltrue', exe15)
test('nequalfalse', exe16)
