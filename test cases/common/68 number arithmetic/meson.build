project('number arithmetic', 'c')

if 6 + 4 != 10
  error('Number addition is broken')
endif
if 6 - 4 != 2
  error('Number subtraction is broken')
endif

if 6 * 4 != 24
  error('Number multiplication is broken')
endif
if 16 / 4 != 4
  error('Number division is broken')
endif

#if (1 / 3) * 3 != 1
#  error('Float interconversion broken')
#endif
if (5 / 3) * 3 != 3
  error('Integer division is broken')
endif

assert(3 < 4, 'Lt broken')
assert(not(4 < 3), 'Lt broken')
assert(3 <= 4, 'Lte broken')
assert(not(4 <= 3), 'Lte broken')
assert(3 <= 3, 'Lte broken')

assert(4 > 3, 'Gt broken')
assert(not(3 > 4), 'Gt broken')
assert(4 >= 3, 'Gte broken')
assert(not(3 >= 4), 'Gte broken')
assert(3 >= 3, 'Gte broken')

assert(true.to_int() == 1,'bool to_int() broken')
assert(false.to_int() == 0,'bool to_int() broken')
