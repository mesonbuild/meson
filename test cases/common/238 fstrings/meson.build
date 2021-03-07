project('meson-test', 'c')

n = 10
m = 'bar'
s = f'test {n} string ({n}): {m}'

if s != 'test 10 string (10): bar'
  error('Incorrect string formatting')
endif
